import os
import requests
import math

GITHUB_TOKEN = os.environ['GITHUB_TOKEN']
GITHUB_USER  = os.environ.get('GITHUB_ACTOR', '')

COLORS = {
    0: '#161b22',
    1: '#2d1b69',
    2: '#6a0dad',
    3: '#9b59b6',
    4: '#c39bd3',
}

DOT_S   = 11
DOT_GAP = 14
PAD_X   = 20
PAD_Y   = 28
ROWS    = 7
SNAKE_C = '#a855f7'
SNAKE_H = '#d8b4fe'
BG      = '#0d1117'
DURATION = 12

def get_contributions():
    query = '''query($u:String!){user(login:$u){contributionsCollection{
      contributionCalendar{weeks{contributionDays{contributionCount}}}}}}'''
    r = requests.post(
        'https://api.github.com/graphql',
        json={'query': query, 'variables': {'u': GITHUB_USER}},
        headers={'Authorization': f'Bearer {GITHUB_TOKEN}'}
    )
    weeks = r.json()['data']['user']['contributionsCollection']['contributionCalendar']['weeks']
    dots = []
    for col, week in enumerate(weeks):
        for row, day in enumerate(week['contributionDays']):
            dots.append({'col': col, 'row': row, 'count': day['contributionCount']})
    return dots

def level(c):
    if c == 0: return 0
    if c <= 3:  return 1
    if c <= 6:  return 2
    if c <= 9:  return 3
    return 4

def center(col, row):
    return PAD_X + col * DOT_GAP + DOT_S // 2, PAD_Y + row * DOT_GAP + DOT_S // 2

def build_path(cols):
    pts = []
    for col in range(cols):
        rows = range(ROWS) if col % 2 == 0 else range(ROWS - 1, -1, -1)
        for row in rows:
            cx, cy = center(col, row)
            pts.append((cx, cy, col, row))
    return pts

def path_length(pts):
    total = 0
    for i in range(1, len(pts)):
        dx = pts[i][0] - pts[i-1][0]
        dy = pts[i][1] - pts[i-1][1]
        total += math.sqrt(dx*dx + dy*dy)
    return total

def cum_lengths(pts):
    lengths = [0]
    for i in range(1, len(pts)):
        dx = pts[i][0] - pts[i-1][0]
        dy = pts[i][1] - pts[i-1][1]
        lengths.append(lengths[-1] + math.sqrt(dx*dx + dy*dy))
    return lengths

def generate(dots):
    cols = max(d['col'] for d in dots) + 1
    W = PAD_X * 2 + (cols - 1) * DOT_GAP + DOT_S
    H = PAD_Y * 2 + (ROWS  - 1) * DOT_GAP + DOT_S

    pts      = build_path(cols)
    total    = path_length(pts)
    clens    = cum_lengths(pts)
    TAIL_LEN = 55

    path_d = 'M ' + ' L '.join(f'{p[0]} {p[1]}' for p in pts)

    dot_map = {(d['col'], d['row']): d for d in dots}

    lines = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">')
    lines.append(f'<rect width="{W}" height="{H}" fill="{BG}" rx="10"/>')

    for pt in pts:
        col, row = pt[2], pt[3]
        d  = dot_map.get((col, row), {'count': 0})
        lv = level(d['count'])
        x  = PAD_X + col * DOT_GAP
        y  = PAD_Y + row * DOT_GAP

        idx      = next(i for i, p in enumerate(pts) if p[2] == col and p[3] == row)
        dist_here = clens[idx]
        t_eat    = dist_here / total

        t0 = max(0.0, t_eat - 0.02)
        t1 = min(1.0, t_eat + 0.04)

        # Dot fades out when snake eats it, reappears at end of cycle
        if lv > 0:
            kts  = f'0;{t0:.3f};{t1:.3f};1'
            vals = '1;1;0;1'
            lines.append(
                f'<rect x="{x}" y="{y}" width="{DOT_S}" height="{DOT_S}" fill="{COLORS[lv]}" rx="3">'
                f'<animate attributeName="opacity" values="{vals}" keyTimes="{kts}" dur="{DURATION}s" repeatCount="indefinite"/>'
                f'</rect>'
            )
        else:
            lines.append(f'<rect x="{x}" y="{y}" width="{DOT_S}" height="{DOT_S}" fill="{COLORS[0]}" rx="3"/>')

    # Snake body — animated dash
    lines.append(
        f'<path d="{path_d}" fill="none" stroke="{SNAKE_C}" stroke-width="9" '
        f'stroke-linecap="round" stroke-linejoin="round" '
        f'stroke-dasharray="{TAIL_LEN} {total + TAIL_LEN}">'
        f'<animate attributeName="stroke-dashoffset" '
        f'values="{TAIL_LEN};{-(total + 5)}" '
        f'dur="{DURATION}s" repeatCount="indefinite" calcMode="linear"/>'
        f'</path>'
    )

    # Snake head — follows path using animateMotion
    lines.append(
        f'<circle r="7" fill="{SNAKE_H}">'
        f'<animateMotion dur="{DURATION}s" repeatCount="indefinite" calcMode="linear">'
        f'<mpath href="#sp"/>'
        f'</animateMotion>'
        f'</circle>'
    )

    # Hidden path for head motion
    lines.append(f'<path id="sp" d="{path_d}" fill="none" stroke="none"/>')
    lines.append('</svg>')

    return '\n'.join(lines)


print("Fetching contributions...")
dots = get_contributions()
print(f"Got {len(dots)} days")
svg = generate(dots)

os.makedirs('dist', exist_ok=True)
for name in ['github-contribution-grid-snake-dark.svg',
             'github-contribution-grid-snake.svg']:
    with open(f'dist/{name}', 'w') as f:
        f.write(svg)

print("Done! Snake generated.")
