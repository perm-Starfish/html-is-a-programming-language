# https://chatgpt.com/share/690473d7-4388-8007-84c8-dcbebc8c4a4a

# Set board size on the very first line, per assignment
W, H = 10, 10  # width, height (adjust as you like)

import random
import string
import sys
from typing import List, Tuple, Dict, Optional, Set

# =======================
# Configuration toggles
# =======================
SEED = None            # set to an int for reproducible puzzles, e.g., 42
ALLOW_TURNS = True     # False = straight-line only; True = harder mode (can turn, no immediate U-turn)
WORDLIST_FILE = "wordlist.txt"

# =======================
# Helper Types
# =======================
Coord = Tuple[int, int]  # (x, y)
Path = List[Coord]

# 8 directions (dx, dy): N, NE, E, SE, S, SW, W, NW
DIRS: List[Coord] = [
    (0, -1), (1, -1), (1, 0), (1, 1),
    (0, 1), (-1, 1), (-1, 0), (-1, -1)
]

def opposite_dir(d: Coord) -> Coord:
    return (-d[0], -d[1])

# =======================
# Board class
# =======================
class Board:
    def __init__(self, w: int, h: int):
        self.w = w
        self.h = h
        # store board as uppercase letters or None
        self.grid: List[List[Optional[str]]] = [[None for _ in range(w)] for _ in range(h)]
    
    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.w and 0 <= y < self.h
    
    def get(self, x: int, y: int) -> Optional[str]:
        return self.grid[y][x]
    
    def set(self, x: int, y: int, ch: str) -> None:
        self.grid[y][x] = ch
    
    def fill_random(self) -> None:
        for y in range(self.h):
            for x in range(self.w):
                if self.grid[y][x] is None:
                    self.grid[y][x] = random.choice(string.ascii_uppercase)

    def render(self, lowercase_coords: Optional[Set[Coord]] = None) -> str:
        lines = []
        for y in range(self.h):
            row_chars = []
            for x in range(self.w):
                ch = self.grid[y][x]
                if ch is None:
                    ch = "."
                if lowercase_coords and (x, y) in lowercase_coords:
                    row_chars.append(ch.lower())
                else:
                    row_chars.append(ch.upper())
            lines.append(" ".join(row_chars))
        return "\n".join(lines)

# =======================
# Word placement helpers
# =======================
def load_words(path: str) -> List[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = [ln.strip() for ln in f]
    except FileNotFoundError:
        print(f"Error: '{path}' not found. Please create it with your word list, one per line.")
        sys.exit(1)
    words = []
    for w in raw:
        # keep only letters, lowercase
        cleaned = "".join(ch for ch in w.lower() if ch.isalpha())
        if cleaned:
            words.append(cleaned)
    # de-duplicate while preserving order
    seen = set()
    uniq = []
    for w in words:
        if w not in seen:
            seen.add(w)
            uniq.append(w)
    return uniq

def all_start_positions(w: int, h: int) -> List[Coord]:
    coords = [(x, y) for y in range(h) for x in range(w)]
    random.shuffle(coords)
    return coords

def shuffled_dirs() -> List[Coord]:
    d = DIRS[:]
    random.shuffle(d)
    return d

def can_place_straight(board: Board, word: str, x: int, y: int) -> Optional[Path]:
    """Try to place 'word' in any straight direction starting at (x,y). Return path if fits."""
    # Quick reject: starting cell must be empty or match first letter
    first = board.get(x, y)
    if first is not None and first != word[0].upper():
        return None
    
    for dx, dy in shuffled_dirs():
        path = [(x, y)]
        ok = True
        cx, cy = x, y
        for i in range(1, len(word)):
            cx += dx
            cy += dy
            if not board.in_bounds(cx, cy):
                ok = False
                break
            cell = board.get(cx, cy)
            if cell is not None and cell != word[i].upper():
                ok = False
                break
            path.append((cx, cy))
        if ok:
            return path
    return None

def can_place_turning(board: Board, word: str, start: Coord) -> Optional[Path]:
    """DFS search allowing turns; cannot immediately reverse direction."""
    x0, y0 = start
    first = board.get(x0, y0)
    if first is not None and first != word[0].upper():
        return None
    
    # We’ll try all initial directions from the first letter to the second letter
    # For 1-letter words (unlikely here), we just accept the start.
    if len(word) == 1:
        return [start]
    
    # Prepare a small DFS with pruning
    # Note: same cell can be revisited by turning paths **only** if the letter matches
    # and we are not violating direction rule. (The prompt doesn't forbid revisiting)
    # To stay safe, avoid immediate cycles by tracking (index, x, y, prev_dir) states visited.
    # But with letter constraints and board size, brute DFS is OK.
    visited_states = set()
    
    def dfs(idx: int, x: int, y: int, prev_dir: Optional[Coord], path: Path) -> Optional[Path]:
        # idx is index of next letter to place (we already placed word[idx-1] at (x,y))
        if idx == len(word):
            return path
        
        # Try all directions except immediate U-turn
        dirs = shuffled_dirs()
        for dx, dy in dirs:
            if prev_dir is not None and (dx, dy) == opposite_dir(prev_dir):
                continue
            nx, ny = x + dx, y + dy
            if not board.in_bounds(nx, ny):
                continue
            cell = board.get(nx, ny)
            needed = word[idx].upper()
            if cell is not None and cell != needed:
                continue
            state = (idx, nx, ny, dx, dy)
            if state in visited_states:
                continue
            visited_states.add(state)
            res = dfs(idx + 1, nx, ny, (dx, dy), path + [(nx, ny)])
            if res is not None:
                return res
        return None
    
    # Ensure starting cell is in the path
    start_path = [start]
    # If len(word) > 1, we try to place the second letter onward
    return dfs(1, x0, y0, None, start_path)

def place_word(board: Board, word: str, path: Path) -> None:
    for (x, y), ch in zip(path, word.upper()):
        board.set(x, y, ch)

# =======================
# Main building logic
# =======================
def build_puzzle(w: int, h: int, words: List[str], allow_turns: bool):
    board = Board(w, h)
    words_shuffled = words[:]
    random.shuffle(words_shuffled)
    
    placed: Dict[str, Path] = {}
    
    for word in words_shuffled:
        # generate randomized starting positions
        for (sx, sy) in all_start_positions(board.w, board.h):
            # First-letter quick reject per assignment (unless match)
            first_cell = board.get(sx, sy)
            if first_cell is not None and first_cell != word[0].upper():
                continue
            
            # Try straight or turning modes
            path = None
            if allow_turns:
                path = can_place_turning(board, word, (sx, sy))
            else:
                path = can_place_straight(board, word, sx, sy)
            
            if path is not None:
                # Final safety: verify every cell matches or is empty
                ok = True
                for (x, y), ch in zip(path, word.upper()):
                    cell = board.get(x, y)
                    if cell is not None and cell != ch:
                        ok = False
                        break
                if not ok:
                    continue
                place_word(board, word, path)
                placed[word] = path
                break  # move to next word
    
    # Fill in the rest
    board.fill_random()
    
    # Alphabetical list of actually included words
    included_sorted = sorted(placed.keys())
    return board, placed, included_sorted

# =======================
# Interactive highlighting
# =======================
def highlight_loop(board: Board, placed: Dict[str, Path], _included_sorted_ignored: List[str]) -> None:
    # Recompute included words from the board + recorded paths
    def recompute_included() -> List[str]:
        included = []
        for w, path in placed.items():
            if len(path) != len(w):
                continue
            ok = True
            for (x, y), ch in zip(path, w):
                if board.get(x, y) != ch.upper():
                    ok = False
                    break
            if ok:
                included.append(w)
        return sorted(included)

    included_sorted = recompute_included()
    print(board.render())
    print()
    print(", ".join(included_sorted))
    print()

    while True:
        try:
            entry = input("Type a word to highlight (Enter to quit, '?' to list words): ").strip().lower()
        except EOFError:
            break
        if entry == "":
            break
        if entry == "?":
            included_sorted = recompute_included()
            print(", ".join(included_sorted))
            print()
            continue
        if entry in placed:
            coords = set(placed[entry])
            print()
            print(board.render(lowercase_coords=coords))
            print()
        else:
            print(f"'{entry}' was not placed on the board (or not in the list).")
            print()
            print(board.render())
            print()

# =======================
# Entrypoint
# =======================
def main():
    if SEED is not None:
        random.seed(SEED)
    words = load_words(WORDLIST_FILE)
    board, placed, included_sorted = build_puzzle(W, H, words, ALLOW_TURNS)
    highlight_loop(board, placed, included_sorted)

if __name__ == "__main__":
    main()
