#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError

from utils import utc_now_iso, make_id, jitter_sleep, parse_bool, get_logger, json_dumps
from db import connect, upsert_comments
from rules import rule_score
import l8_selectors as sel  # ensure file was renamed from selectors.py


# ---------- Config ----------
def load_env():
    load_dotenv()
    cfg = {
        "PROFILE_URL": os.getenv("PROFILE_URL"),
        "DB_PATH": os.getenv("DB_PATH", "lemon8_comments.sqlite"),
        "MAX_POSTS": int(os.getenv("MAX_POSTS", "12")),
        "USE_DETOX": parse_bool(os.getenv("USE_DETOX", "0")),
        "TOXIC_THRESH": float(os.getenv("TOXIC_THRESH", "0.78")),
        "RULE_THRESH": float(os.getenv("RULE_THRESH", "3.0")),
        "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
    }
    return cfg


# ---------- Debug helpers ----------
def ts():
    return datetime.utcnow().strftime("%Y%m%d-%H%M%S")

def ensure_debug_dir() -> Path:
    d = Path("debug")
    d.mkdir(parents=True, exist_ok=True)
    return d

def save_debug(page, label: str, log):
    debug_dir = ensure_debug_dir()
    base = f"{label}-{ts()}"
    html_path = debug_dir / f"{base}.html"
    png_path = debug_dir / f"{base}.png"
    try:
        html_path.write_text(page.content(), encoding="utf-8")
        page.screenshot(path=str(png_path), full_page=True)
        log.warning(f"[DEBUG] Saved snapshot: {html_path} and {png_path}")
    except Exception as e:
        log.error(f"[DEBUG] Failed to save snapshot: {e}")


# ---------- Contexts & UA ----------
ANDROID_UA = (
    "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36"
)
DESKTOP_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

def make_context(browser, desktop=False):
    if not desktop:
        return browser.new_context(
            viewport={"width": 412, "height": 915},
            device_scale_factor=2.625,
            is_mobile=True,
            has_touch=True,
            user_agent=ANDROID_UA,
        )
    # desktop fallback (sometimes avoids mobile SEO/app walls)
    return browser.new_context(
        viewport={"width": 1366, "height": 900},
        device_scale_factor=1.0,
        is_mobile=False,
        has_touch=False,
        user_agent=DESKTOP_UA,
    )


# ---------- App-wall killer ----------
BLOCK_PATTERNS = [
    # block known/open-app/landing assets & deeplinks
    r"/seo-landing", r"/openapp", r"/open-app", r"/open_in_app",
    r"/appdownload", r"/app-download", r"/install", r"/jump/download",
    r"tmall|appsflyer|adjust|branch\.io|smartlink|smartapp",
]

REMOVE_SELECTORS = [
    ".seo-landing-modal-wrapper",
    ".seo-landing-modal-style-wrapper",
    ".ui-mobile-drawer-container",
    ".ban-banner-wrapper",
    ".bottom-reflow",
    "[class*='OpenApp']", "[data-open-app]",
    "div[role='dialog']",
]

CSS_SUPPRESS = """
  /* hide fixed overlays that often block scrolling/clicks */
  .seo-landing-modal-wrapper,
  .seo-landing-modal-style-wrapper,
  .ui-mobile-drawer-container,
  .ban-banner-wrapper,
  .bottom-reflow {
    display: none !important; opacity: 0 !important; visibility: hidden !important;
    pointer-events: none !important;
  }
  body { overflow: auto !important; }
"""

MUTATION_OBSERVER_JS = """
(() => {
  try {
    const kill = () => {
      const sels = %s;
      let removed = 0;
      for (const s of sels) {
        document.querySelectorAll(s).forEach(el => { el.remove(); removed++; });
      }
      // also remove any full-screen divs with huge z-index
      [...document.querySelectorAll('div')]
        .filter(d => {
          const st = getComputedStyle(d);
          return (st.position === 'fixed' || st.position === 'sticky') &&
                 parseInt(st.zIndex || '0', 10) >= 1000 &&
                 (d.offsetHeight > window.innerHeight*0.6 || d.offsetWidth > window.innerWidth*0.6);
        })
        .forEach(d => { d.remove(); removed++; });
      if (removed > 0) { document.body.style.overflow = 'auto'; }
    };
    kill();
    const mo = new MutationObserver(() => kill());
    mo.observe(document.documentElement, {childList: true, subtree: true});
  } catch (e) {}
})();
""" % (json.dumps(REMOVE_SELECTORS))

def install_appwall_blockers(context, page, log):
    # 1) Block requests that look like app-wall/landing/installer
    def route_handler(route):
        url = route.request.url.lower()
        for pat in BLOCK_PATTERNS:
            if re.search(pat, url):
                return route.abort()  # drop it
        return route.continue_()
    try:
        context.route("**/*", route_handler)
    except Exception:
        pass

    # 2) Add CSS to suppress known wrappers
    try:
        page.add_style_tag(content=CSS_SUPPRESS)
    except Exception:
        pass

    # 3) Install a mutation observer to auto-remove overlays forever
    try:
        page.add_init_script(MUTATION_OBSERVER_JS)
    except Exception:
        pass


def nuke_overlays(page):
    # attempt removal + ESC
    try:
        page.evaluate(MUTATION_OBSERVER_JS)
    except Exception:
        pass
    try:
        page.keyboard.press("Escape")
    except Exception:
        pass


# ---------- URL helpers ----------
def normalize_post_url(url: str) -> str:
    if not url:
        return url
    if "region=" not in url.lower():
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}region=US"
    if "#comments" not in url:
        url = f"{url}#comments"
    return url


# ---------- Link harvesting ----------
def _extract_links_from_dom(page, patterns: List[str]) -> List[str]:
    hrefs = page.eval_on_selector_all(
        "a",
        "els => els.map(e => (e.href || e.getAttribute('href'))).filter(Boolean)"
    ) or []
    hrefs += page.eval_on_selector_all(
        "[data-href]",
        "els => els.map(e => e.getAttribute('data-href')).filter(Boolean)"
    ) or []
    uniq = []
    for h in hrefs:
        s = str(h)
        for pat in patterns:
            if re.search(pat, s):
                if s not in uniq:
                    uniq.append(s)
                break
    return uniq

def _extract_links_from_json_scripts(page, patterns: List[str], max_scripts: int = 40) -> List[str]:
    links: List[str] = []
    scripts = page.locator("script")
    count = scripts.count()
    for i in range(min(count, max_scripts)):
        try:
            raw = scripts.nth(i).inner_text(timeout=600)
        except Exception:
            continue
        if not raw or ("post" not in raw and "article" not in raw and "share" not in raw):
            continue
        for pat in patterns:
            for m in re.findall(pat, raw):
                if m not in links:
                    links.append(m)
    return links

def get_post_links_from_profile(page, max_posts: int, log) -> List[str]:
    patterns = [
        r"https?://[^\s\"'>]+/post/[^\s\"'>]+",
        r"https?://[^\s\"'>]+/article/[^\s\"'>]+",
        r"https?://[^\s\"'>]+/share/post/[^\s\"'>]+",
        r"https?://[^\s\"'>]+/@[^\s\"'>]+/\d+",   # direct numeric id path
    ]

    page.wait_for_timeout(600)
    nuke_overlays(page)

    seen: List[str] = []
    failures = 0
    last = -1

    for _ in range(22):  # a bit more scrolls
        for u in _extract_links_from_dom(page, patterns):
            if u not in seen:
                seen.append(u)
        for u in _extract_links_from_json_scripts(page, patterns):
            if u not in seen:
                seen.append(u)

        if len(seen) >= max_posts:
            break

        # scroll + keep killing overlays
        page.evaluate("window.scrollBy(0, Math.floor(window.innerHeight*0.9));")
        page.wait_for_timeout(500)
        nuke_overlays(page)

        if len(seen) == last:
            failures += 1
            page.evaluate("window.scrollBy(0, -Math.floor(window.innerHeight*0.4));")
            page.wait_for_timeout(300)
            nuke_overlays(page)
        else:
            failures = 0
            last = len(seen)

        if failures >= 3:
            break

    # normalize & uniq by path
    out = [normalize_post_url(u) for u in seen]
    uniq, seen_path = [], set()
    for u in out:
        path = re.sub(r"[?#].*$", "", u)
        if path not in seen_path:
            seen_path.add(path)
            uniq.append(u)
        if len(uniq) >= max_posts:
            break
    return uniq


# ---------- Comments ----------
def try_open_comments_tab(page):
    choices = [
        "text=/^Comments?\\b/i",
        "button:has-text('Comments')",
        "a:has-text('Comments')",
        "[role=tab]:has-text('Comments')",
        "[data-tab='comments']",
    ]
    for s in choices:
        try:
            el = page.locator(s).first
            if el and el.is_visible():
                el.click()
                page.wait_for_timeout(400)
                return True
        except Exception:
            continue
    return False

def load_more_comments(page, target_min=60, max_cycles=32):
    containers = [
        "[class*='comment'] [class*='list']",
        "[class*='Comments'] [class*='list']",
        "[data-scroll='comments']",
        "section[role='feed']",
    ]
    item_selectors = [
        ".article-comment-item-wrapper .article-comment-item",
        ".comment-reply-list .article-comment-item",
        "[class*='comment'] [class*='item']",
        "[data-e2e*='comment']",
    ]
    def count_items():
        total = 0
        for css in item_selectors:
            try:
                total += page.locator(css).count()
            except Exception:
                pass
        return total

    last, cycles = -1, 0
    while cycles < max_cycles:
        # scroll container if visible, else page
        scrolled = False
        for ccss in containers:
            try:
                cont = page.locator(ccss).first
                if cont and cont.is_visible():
                    page.evaluate("el => el.scrollBy(0, Math.floor(el.clientHeight*0.9));", cont)
                    scrolled = True
                    break
            except Exception:
                pass
        if not scrolled:
            page.evaluate("window.scrollBy(0, Math.floor(window.innerHeight*0.9));")

        page.wait_for_timeout(350)
        nuke_overlays(page)
        cur = count_items()
        if cur == last:
            try:
                for ccss in containers:
                    cont = page.locator(ccss).first
                    if cont and cont.is_visible():
                        page.evaluate("el => el.scrollBy(0, -Math.floor(el.clientHeight*0.4));", cont)
                        break
                else:
                    page.evaluate("window.scrollBy(0, -Math.floor(window.innerHeight*0.4));")
            except Exception:
                pass
            page.wait_for_timeout(250)
            nuke_overlays(page)
            cur = count_items()
            if cur == last:
                break
        last = cur
        cycles += 1
        if cur >= target_min:
            break

def expand_all_comments(page):
    for ex in sel.EXPANDERS:
        try:
            while page.locator(ex).first.is_visible():
                page.locator(ex).first.click()
                page.wait_for_timeout(250)
        except Exception:
            continue

def extract_comments(page) -> Tuple[str, List[Dict[str, Any]]]:
    try:
        post_title = page.title()
    except Exception:
        post_title = None

    comments: List[Dict[str, Any]] = []
    found = False

    for css in sel.COMMENT_ITEMS:
        loc = page.locator(css)
        try:
            count = loc.count()
        except Exception:
            count = 0
        for i in range(count):
            try:
                item = loc.nth(i)
                text = item.inner_text(timeout=1500).strip()
                if not text:
                    continue
                lines = [l.strip() for l in text.splitlines() if l.strip()]
                if not lines:
                    continue
                author = lines[0][:80]
                body = " ".join(lines[1:]) if len(lines) > 1 else ""
                comments.append({"author": author, "text": body})
                found = True
            except PWTimeoutError:
                continue
            except Exception:
                continue

    if found and comments:
        return post_title, comments

    # JSON-LD fallback
    scripts = page.locator('script[type="application/ld+json"]')
    try:
        scount = scripts.count()
    except Exception:
        scount = 0
    for i in range(scount):
        try:
            raw = scripts.nth(i).inner_text(timeout=800)
            data = json.loads(raw)
            if isinstance(data, dict) and "comment" in data:
                for c in data.get("comment") or []:
                    author = c.get("author", None)
                    if isinstance(author, dict):
                        author = author.get("name")
                    text = c.get("text")
                    if text:
                        comments.append({"author": author, "text": text})
        except Exception:
            continue
    return post_title, comments


# ---------- Scoring ----------
def detox_scores(texts: List[str]):
    try:
        from detoxify import Detoxify
        model = Detoxify("multilingual")
        res = model.predict(texts)
        keys = list(res.keys())
        out = []
        for i in range(len(texts)):
            out.append({k: float(res[k][i]) for k in keys})
        return out
    except Exception:
        return [None for _ in texts]

def score_and_flag(cfg, comments: List[Dict[str, Any]]):
    texts = [c.get("text") or "" for c in comments]
    ml_scores = detox_scores(texts) if cfg["USE_DETOX"] else [None for _ in texts]
    out = []
    for i, c in enumerate(comments):
        rs = float(rule_score(c.get("text") or ""))
        ms = ml_scores[i]
        flagged = rs >= cfg["RULE_THRESH"] or (ms and any(v >= cfg["TOXIC_THRESH"] for v in ms.values()))
        out.append((rs, ms, flagged))
    return out


# ---------- Crawlers ----------
def crawl_single_url(cfg, browser, url: str, log, try_desktop=False):
    ctx = make_context(browser, desktop=try_desktop)
    page = ctx.new_page()
    page.set_default_timeout(12000)
    install_appwall_blockers(ctx, page, log)
    try:
        url = normalize_post_url(url)
        page.goto(url, wait_until="domcontentloaded", timeout=35000)
        page.wait_for_load_state("networkidle", timeout=15000)
        nuke_overlays(page)

        try_opened = try_open_comments_tab(page)
        for _ in range(3):
            page.evaluate("window.scrollBy(0, Math.floor(window.innerHeight*0.9));")
            page.wait_for_timeout(250)
            nuke_overlays(page)
        load_more_comments(page, target_min=60, max_cycles=32)
        expand_all_comments(page)

        post_title, comments = extract_comments(page)
        if not comments and not try_desktop:
            # fallback once with desktop UA
            log.info("No comments found; retrying with desktop UA fallback.")
            return crawl_single_url(cfg, browser, url, log, try_desktop=True)

        if not comments:
            log.warning("No comments found via DOM/JSON-LD; saving snapshot.")
            save_debug(page, "no-comments", log)
            return post_title, []

        scored = score_and_flag(cfg, comments)
        scraped_at = utc_now_iso()
        rows = []
        for c, (rs, ms, flagged) in zip(comments, scored):
            cid = make_id(url, c.get("author") or "", c.get("text") or "")
            rows.append({
                "id": cid, "post_url": url, "post_title": post_title,
                "author": c.get("author"), "text": c.get("text"),
                "scraped_at": scraped_at,
                "model_scores": json_dumps(ms) if ms else None,
                "rule_score": rs, "flagged": flagged,
            })
        return post_title, rows
    finally:
        ctx.close()

def crawl_profile(cfg, browser, profile_url: str, log, try_desktop=False):
    ctx = make_context(browser, desktop=try_desktop)
    page = ctx.new_page()
    page.set_default_timeout(12000)
    install_appwall_blockers(ctx, page, log)
    posts_all: List[Dict[str, Any]] = []
    try:
        # load + region hint retry
        try:
            page.goto(profile_url, wait_until="domcontentloaded", timeout=35000)
            page.wait_for_load_state("networkidle", timeout=15000)
        except PWTimeoutError:
            sep = "&" if "?" in profile_url else "?"
            alt = f"{profile_url}{sep}region=US"
            page.goto(alt, wait_until="domcontentloaded", timeout=35000)
            page.wait_for_load_state("networkidle", timeout=15000)

        nuke_overlays(page)
        jitter_sleep()

        posts = get_post_links_from_profile(page, cfg["MAX_POSTS"], log)
        if not posts and not try_desktop:
            log.info("No post links; retrying profile with desktop UA fallback.")
            ctx.close()
            return crawl_profile(cfg, browser, profile_url, log, try_desktop=True)

        if not posts:
            log.warning("No post links found after scroll/parsing; saving snapshot.")
            save_debug(page, "no-post-links", log)
            return []

        log.info("Found post links:\n" + "\n".join(posts))
        for p in posts:
            jitter_sleep(0.6, 1.2)
            _, rows = crawl_single_url(cfg, browser, p, log)
            posts_all.extend(rows)
        return posts_all
    finally:
        ctx.close()


# ---------- Main ----------
def main():
    cfg = load_env()
    log = get_logger(cfg["LOG_LEVEL"])
    parser = argparse.ArgumentParser(description="Lemon8 comment monitor")
    parser.add_argument("--profile-url", default=cfg["PROFILE_URL"], help="Profile URL")
    parser.add_argument("--single-url", help="Single post URL")
    parser.add_argument("--max-posts", type=int, default=cfg["MAX_POSTS"])
    parser.add_argument("--headful", action="store_true", help="Run with browser UI (debug)")
    args = parser.parse_args()

    if not args.profile_url and not args.single_url:
        log.error("Provide --profile-url or --single-url (or set PROFILE_URL in .env).")
        sys.exit(3)

    cfg["MAX_POSTS"] = args.max_posts

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headful)
        conn = connect(cfg["DB_PATH"])
        try:
            if args.single_url:
                _, rows = crawl_single_url(cfg, browser, args.single_url, log)
                upsert_comments(conn, rows)
                log.info(f"Saved {len(rows)} comments from single URL.")
            else:
                rows = crawl_profile(cfg, browser, args.profile_url, log)
                upsert_comments(conn, rows)
                log.info(f"Saved {len(rows)} comments from profile crawl.")
        finally:
            browser.close()


if __name__ == "__main__":
    main()
