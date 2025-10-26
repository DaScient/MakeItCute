import pygame, telnetlib, threading, queue, time

# -- Setup Pygame Terminal --
pygame.init()
width, height = 1200, 900
screen = pygame.display.set_mode((width, height))
font = pygame.font.SysFont('Courier New', 22)
lines = []
fx_queue = queue.Queue()

# -- Telnet Thread --
def mud_listener(host, port):
    tn = telnetlib.Telnet(host, port)
    while True:
        data = tn.read_very_eager()
        if data:
            s = data.decode('utf8', errors='replace')
            for line in s.splitlines():
                lines.append(line)
                # FX triggers: demo, triggers for ASCII art or words
                if "attack" in line.lower() or "kills" in line.lower():
                    fx_queue.put("explosion")
                if "level" in line.lower():
                    fx_queue.put("confetti")
                if any(c in line for c in "/\\|_[]{}()#@"):
                    fx_queue.put("asciiart")
        time.sleep(0.02)

# -- Demo: Connect to telehack.com --
threading.Thread(target=mud_listener, args=('telehack.com', 23), daemon=True).start()

# -- FX Handler: Overlay visuals for FX triggers
def draw_fx(screen, fx_type):
    if fx_type == "explosion":
        for _ in range(140):
            x, y = width//2 + int((random.random()-0.5)*600), height//2 + int((random.random()-0.5)*600)
            r = random.randint(3, 10)
            color = (255, random.randint(50, 200), random.randint(50, 255))
            pygame.draw.circle(screen, color, (x, y), r)
    elif fx_type == "confetti":
        for _ in range(250):
            x, y = random.randint(0, width), random.randint(0, height)
            color = (random.randint(150,255),random.randint(130,255),random.randint(180,255))
            pygame.draw.circle(screen, color, (x, y), 2)
    elif fx_type == "asciiart":
        for _ in range(30):
            x, y = random.randint(0, width), random.randint(0, height)
            color = (random.randint(180,255),255,255)
            pygame.draw.circle(screen, color, (x, y), random.randint(5, 20), 2)

# -- Main Loop --
scroll = 0
running = True
while running:
    screen.fill((12, 13, 18))
    # Draw text window (latest at bottom)
    show = lines[-38+scroll:scroll] if len(lines) > 38 else lines
    for i, line in enumerate(show):
        surf = font.render(line[:200], True, (220, 255, 220))
        screen.blit(surf, (18, 22+i*22))
    # Draw FX if any
    try:
        fx = fx_queue.get_nowait()
        draw_fx(screen, fx)
    except queue.Empty:
        pass
    pygame.display.flip()
    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_DOWN: scroll = min(scroll+1, len(lines))
            if event.key == pygame.K_UP: scroll = max(scroll-1, 0)
pygame.quit()
