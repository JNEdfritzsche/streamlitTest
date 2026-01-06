import streamlit as st
import datetime
import random
import hashlib
from typing import List, Dict, Tuple

# -----------------------------
# Config
# -----------------------------
st.set_page_config(page_title="Wordle-like", page_icon="🟩", layout="centered")

WORD_LENGTH = 5
MAX_GUESSES = 6

# A small built-in list so this works out of the box.
# You can replace/extend this with a bigger list later.
SOLUTION_WORDS = [
    "CRANE", "SLATE", "TRACE", "ROAST", "SHARE", "POINT", "MIGHT", "SOUND", "HEART", "WATER",
    "SMILE", "BRICK", "PLANT", "GRACE", "CHOIR", "GHOST", "CLOUD", "NURSE", "WORLD", "STORY",
    "HOUSE", "LIGHT", "NIGHT", "PARTY", "GREEN", "BLACK", "WHITE", "BROWN", "LEMON", "BERRY",
    "FAITH", "MOVIE", "MONEY", "PIZZA", "CANDY", "SUGAR", "SWEET", "SALAD", "BREAD", "PASTA",
]

# Acceptable guesses: include solution words plus extras (optional).
# For now, keep it simple: accept solutions only.
VALID_GUESSES = set(SOLUTION_WORDS)

# Keyboard layout (Wordle-ish)
KEY_ROWS = [
    list("QWERTYUIOP"),
    list("ASDFGHJKL"),
    ["ENTER"] + list("ZXCVBNM") + ["⌫"],
]

# Color priority: green > yellow > gray
PRIORITY = {"correct": 3, "present": 2, "absent": 1, "unused": 0}

# -----------------------------
# Helpers
# -----------------------------
def stable_daily_index(seed: str, n: int) -> int:
    """Deterministic daily index based on date + seed (no external storage)."""
    today = datetime.date.today().isoformat()
    h = hashlib.sha256((today + "::" + seed).encode("utf-8")).hexdigest()
    return int(h[:8], 16) % n

def evaluate_guess(guess: str, answer: str) -> List[str]:
    """
    Returns list of statuses per letter: correct/present/absent
    Wordle-style evaluation with duplicate handling.
    """
    guess = guess.upper()
    answer = answer.upper()

    result = ["absent"] * WORD_LENGTH
    answer_chars = list(answer)

    # First pass: greens
    for i in range(WORD_LENGTH):
        if guess[i] == answer_chars[i]:
            result[i] = "correct"
            answer_chars[i] = None  # consume

    # Second pass: yellows
    for i in range(WORD_LENGTH):
        if result[i] == "correct":
            continue
        if guess[i] in answer_chars:
            result[i] = "present"
            answer_chars[answer_chars.index(guess[i])] = None  # consume

    return result

def update_key_statuses(key_status: Dict[str, str], guess: str, statuses: List[str]) -> Dict[str, str]:
    new = dict(key_status)
    for ch, stt in zip(guess, statuses):
        ch = ch.upper()
        prev = new.get(ch, "unused")
        if PRIORITY[stt] > PRIORITY[prev]:
            new[ch] = stt
    return new

def tile_color(status: str) -> str:
    # Close to Wordle-ish colors but not exact.
    if status == "correct":
        return "#6AAA64"  # green
    if status == "present":
        return "#C9B458"  # yellow
    if status == "absent":
        return "#787C7E"  # gray
    return "#FFFFFF"

def key_color(status: str) -> str:
    if status == "correct":
        return "#6AAA64"
    if status == "present":
        return "#C9B458"
    if status == "absent":
        return "#3A3A3C"
    return "#D3D6DA"

def border_color(status: str) -> str:
    if status in ("correct", "present", "absent"):
        return tile_color(status)
    return "#D3D6DA"

def render_board(guesses: List[str], feedback: List[List[str]], current: str, game_over: bool):
    # Build 6 rows x 5 columns
    rows_html = []
    for r in range(MAX_GUESSES):
        if r < len(guesses):
            word = guesses[r]
            statuses = feedback[r]
            tiles = []
            for i, ch in enumerate(word):
                stt = statuses[i]
                tiles.append(f"""
                    <div class="tile filled"
                         style="background:{tile_color(stt)}; border-color:{border_color(stt)};">
                        {ch}
                    </div>
                """)
            rows_html.append(f"""<div class="row">{''.join(tiles)}</div>""")
        elif r == len(guesses) and not game_over:
            # Active row (current typing)
            tiles = []
            for i in range(WORD_LENGTH):
                ch = current[i] if i < len(current) else ""
                filled_class = "filled" if ch else ""
                tiles.append(f"""
                    <div class="tile {filled_class}">
                        {ch}
                    </div>
                """)
            rows_html.append(f"""<div class="row">{''.join(tiles)}</div>""")
        else:
            # Empty row
            tiles = ["""<div class="tile"></div>""" for _ in range(WORD_LENGTH)]
            rows_html.append(f"""<div class="row">{''.join(tiles)}</div>""")

    st.markdown(
        f"""
        <div class="board">
            {''.join(rows_html)}
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_keyboard(key_status: Dict[str, str]):
    for row in KEY_ROWS:
        cols = st.columns([1] * len(row))
        for i, key in enumerate(row):
            status = key_status.get(key, "unused") if len(key) == 1 else "unused"
            label = key
            width = "100%"
            disabled = False

            # Wider keys
            if key == "ENTER":
                label = "Enter"
            if key == "⌫":
                label = "Backspace"

            btn_style = f"""
            <style>
            div[data-testid="column"]:nth-of-type({i+1}) button {{
                width: {width};
                height: 48px;
                border-radius: 8px;
                border: 0px;
                background: {key_color(status) if len(key) == 1 else "#D3D6DA"};
                color: {"#FFFFFF" if status in ("correct", "present", "absent") else "#111111"};
                font-weight: 700;
                margin: 2px 0px;
            }}
            </style>
            """
            st.markdown(btn_style, unsafe_allow_html=True)

            if cols[i].button(label, key=f"key_{key}"):
                st.session_state.last_key = key

def share_grid(guesses: List[str], feedback: List[List[str]]) -> str:
    lines = []
    for row in feedback:
        s = ""
        for stt in row:
            if stt == "correct":
                s += "🟩"
            elif stt == "present":
                s += "🟨"
            else:
                s += "⬛"
        lines.append(s)
    return "\n".join(lines)

# -----------------------------
# Styles
# -----------------------------
st.markdown(
    """
    <style>
    /* Center content nicely */
    .block-container { max-width: 520px; padding-top: 1.2rem; }

    .titlebar {
        display:flex; align-items:center; justify-content:space-between;
        margin-bottom: 10px;
    }
    .brand {
        font-size: 28px;
        font-weight: 800;
        letter-spacing: 0.06em;
        text-transform: uppercase;
    }
    .subtle { color: #666; font-size: 13px; }

    .board { display:flex; flex-direction:column; gap:8px; margin: 12px 0 10px 0; }
    .row { display:flex; gap:8px; justify-content:center; }

    .tile {
        width: 56px; height: 56px;
        border: 2px solid #D3D6DA;
        display:flex; align-items:center; justify-content:center;
        font-size: 28px; font-weight: 800;
        text-transform: uppercase;
        user-select:none;
        box-sizing:border-box;
        background:#FFFFFF;
    }
    .tile.filled { border-color:#878A8C; }

    /* Make it feel app-like */
    button[kind="secondary"] { border-radius: 10px !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# State init
# -----------------------------
if "answer" not in st.session_state:
    idx = stable_daily_index(seed="streamlit-wordle-like", n=len(SOLUTION_WORDS))
    st.session_state.answer = SOLUTION_WORDS[idx]

if "guesses" not in st.session_state:
    st.session_state.guesses = []

if "feedback" not in st.session_state:
    st.session_state.feedback = []

if "current" not in st.session_state:
    st.session_state.current = ""

if "key_status" not in st.session_state:
    st.session_state.key_status = {}

if "game_over" not in st.session_state:
    st.session_state.game_over = False

if "won" not in st.session_state:
    st.session_state.won = False

if "last_key" not in st.session_state:
    st.session_state.last_key = None

# -----------------------------
# Header
# -----------------------------
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown('<div class="brand">WORDLE-like</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtle">Guess the word in 6 tries.</div>', unsafe_allow_html=True)
with col2:
    if st.button("New (random)"):
        st.session_state.answer = random.choice(SOLUTION_WORDS)
        st.session_state.guesses = []
        st.session_state.feedback = []
        st.session_state.current = ""
        st.session_state.key_status = {}
        st.session_state.game_over = False
        st.session_state.won = False
        st.session_state.last_key = None
        st.rerun()

# -----------------------------
# Game logic functions
# -----------------------------
def commit_guess():
    if st.session_state.game_over:
        return
    guess = st.session_state.current.upper()

    if len(guess) != WORD_LENGTH:
        st.toast("Not enough letters", icon="⚠️")
        return
    if guess not in VALID_GUESSES:
        st.toast("Not in word list", icon="❌")
        return

    statuses = evaluate_guess(guess, st.session_state.answer)
    st.session_state.guesses.append(guess)
    st.session_state.feedback.append(statuses)
    st.session_state.key_status = update_key_statuses(st.session_state.key_status, guess, statuses)
    st.session_state.current = ""

    if guess == st.session_state.answer:
        st.session_state.game_over = True
        st.session_state.won = True
        st.toast("You got it!", icon="🎉")
    elif len(st.session_state.guesses) >= MAX_GUESSES:
        st.session_state.game_over = True
        st.session_state.won = False
        st.toast(f"The word was {st.session_state.answer}", icon="🧠")

def handle_keypress(key: str):
    if st.session_state.game_over:
        return

    if key == "ENTER":
        commit_guess()
        return
    if key == "⌫":
        st.session_state.current = st.session_state.current[:-1]
        return
    if len(key) == 1 and key.isalpha():
        if len(st.session_state.current) < WORD_LENGTH:
            st.session_state.current += key.upper()

# -----------------------------
# Board render
# -----------------------------
render_board(
    guesses=st.session_state.guesses,
    feedback=st.session_state.feedback,
    current=st.session_state.current,
    game_over=st.session_state.game_over
)

# -----------------------------
# Input row (keyboard + optional physical typing)
# -----------------------------
st.markdown("")

# Physical typing fallback (text input)
# (Streamlit doesn't capture raw keypress reliably, so this helps.)
typed = st.text_input(
    "Type here (optional), then press Enter button",
    value=st.session_state.current,
    max_chars=WORD_LENGTH,
    label_visibility="collapsed",
    disabled=st.session_state.game_over,
)
# Keep in sync if user types here
if typed != st.session_state.current and not st.session_state.game_over:
    st.session_state.current = typed.upper()[:WORD_LENGTH]

# Action buttons
b1, b2, b3 = st.columns([1, 1, 1])
with b1:
    if st.button("Enter", use_container_width=True, disabled=st.session_state.game_over):
        commit_guess()
with b2:
    if st.button("Backspace", use_container_width=True, disabled=st.session_state.game_over):
        handle_keypress("⌫")
with b3:
    if st.button("Clear", use_container_width=True, disabled=st.session_state.game_over):
        st.session_state.current = ""

# On-screen keyboard
st.markdown("")
render_keyboard(st.session_state.key_status)

# If a keyboard button was pressed, apply it and rerun
if st.session_state.last_key:
    k = st.session_state.last_key
    st.session_state.last_key = None
    handle_keypress(k)
    st.rerun()

# -----------------------------
# Footer / Results
# -----------------------------
st.markdown("---")

if st.session_state.game_over:
    tries = len(st.session_state.guesses)
    if st.session_state.won:
        st.success(f"Solved in {tries}/{MAX_GUESSES}!")
    else:
        st.error(f"Out of tries. Answer: **{st.session_state.answer}**")

    grid = share_grid(st.session_state.guesses, st.session_state.feedback)
    st.text_area("Share (copy/paste)", value=grid, height=140)

with st.expander("How to play"):
    st.write(
        "- Guess a **5-letter** word in **6** tries.\n"
        "- **Green**: right letter, right spot.\n"
        "- **Yellow**: right letter, wrong spot.\n"
        "- **Gray**: letter not in the word.\n"
    )
