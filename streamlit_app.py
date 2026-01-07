import streamlit as st
import datetime
import random
import hashlib
from typing import List, Dict

# -----------------------------
# Page config
# -----------------------------
st.set_page_config(page_title="Mini Games Arcade", page_icon="🎮", layout="centered")

# -----------------------------
# Global styling (loaded ONCE)
# -----------------------------
st.markdown(
    """
    <style>
    .block-container { max-width: 860px; padding-top: 1.0rem; padding-bottom: 2.5rem; }
    [data-testid="stVerticalBlock"] { gap: 0.65rem; }

    div[data-testid="stToolbar"] { visibility: hidden; height: 0%; position: fixed; }
    header { visibility: hidden; height: 0px; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }

    html, body, [class*="css"] {
        font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;
    }

    .card {
        background: rgba(255,255,255,0.86);
        border: 1px solid rgba(0,0,0,0.08);
        border-radius: 18px;
        padding: 18px 18px 14px 18px;
        box-shadow: 0 8px 22px rgba(0,0,0,0.06);
        backdrop-filter: blur(6px);
    }
    .muted { color: rgba(0,0,0,0.58); font-size: 0.95rem; margin-top: 0.25rem; }

    .hero {
        display:flex; align-items:center; justify-content:space-between;
        gap: 12px;
        padding: 16px 18px;
        border-radius: 18px;
        border: 1px solid rgba(0,0,0,0.08);
        background: linear-gradient(135deg, rgba(255,255,255,0.92), rgba(248,248,255,0.92));
        box-shadow: 0 10px 28px rgba(0,0,0,0.06);
        margin-bottom: 10px;
    }
    .hero-title { font-size: 1.55rem; font-weight: 850; margin: 0; }
    .hero-sub { margin: 0.15rem 0 0 0; color: rgba(0,0,0,0.6); font-size: 0.98rem; }

    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 999px;
        padding: 8px 14px;
        border: 1px solid rgba(0,0,0,0.08);
        background: rgba(255,255,255,0.84);
    }

    .stButton button {
        border-radius: 12px !important;
        font-weight: 750 !important;
        border: 1px solid rgba(0,0,0,0.12) !important;
        padding: 0.55rem 0.85rem !important;
    }

    /* Wordle board */
    .board { display:flex; flex-direction:column; gap:10px; margin: 10px 0 10px 0; }
    .row { display:flex; gap:10px; justify-content:center; }

    .tile {
        width: 56px; height: 56px;
        border: 2px solid rgba(0,0,0,0.14);
        border-radius: 12px;
        display:flex; align-items:center; justify-content:center;
        font-size: 28px; font-weight: 900;
        text-transform: uppercase;
        user-select:none;
        box-sizing:border-box;
        background: rgba(255,255,255,0.95);
        color: #111;
    }
    .tile.filled { border-color: rgba(0,0,0,0.28); }

    /* Tic tac toe grid */
    .ttt {
        display:grid;
        grid-template-columns: repeat(3, 92px);
        gap: 10px;
        justify-content:center;
        margin-top: 8px;
        margin-bottom: 8px;
    }
    .ttt button {
        width: 92px !important;
        height: 92px !important;
        font-size: 34px !important;
        font-weight: 900 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# =============================
# WORD GUESS (Wordle-like)
# =============================
WORD_LENGTH = 5
MAX_GUESSES = 6

SOLUTION_WORDS = [
    "CRANE", "SLATE", "TRACE", "ROAST", "SHARE", "POINT", "MIGHT", "SOUND", "HEART", "WATER",
    "SMILE", "BRICK", "PLANT", "GRACE", "CHOIR", "GHOST", "CLOUD", "NURSE", "WORLD", "STORY",
    "HOUSE", "LIGHT", "NIGHT", "PARTY", "GREEN", "BLACK", "WHITE", "BROWN", "LEMON", "BERRY",
    "FAITH", "MOVIE", "MONEY", "PIZZA", "CANDY", "SUGAR", "SWEET", "SALAD", "BREAD", "PASTA",
]
VALID_GUESSES = set(SOLUTION_WORDS)

KEY_ROWS = [
    list("QWERTYUIOP"),
    list("ASDFGHJKL"),
    ["ENTER"] + list("ZXCVBNM") + ["⌫"],
]

PRIORITY = {"correct": 3, "present": 2, "absent": 1, "unused": 0}


def stable_daily_index(seed: str, n: int) -> int:
    today = datetime.date.today().isoformat()
    h = hashlib.sha256((today + "::" + seed).encode("utf-8")).hexdigest()
    return int(h[:8], 16) % n


def evaluate_guess(guess: str, answer: str) -> List[str]:
    """Wordle evaluation with correct duplicate handling."""
    guess = guess.upper()
    answer = answer.upper()

    result = ["absent"] * WORD_LENGTH
    answer_chars = list(answer)

    # Greens
    for i in range(WORD_LENGTH):
        if guess[i] == answer_chars[i]:
            result[i] = "correct"
            answer_chars[i] = None

    # Yellows
    for i in range(WORD_LENGTH):
        if result[i] == "correct":
            continue
        if guess[i] in answer_chars:
            result[i] = "present"
            answer_chars[answer_chars.index(guess[i])] = None

    return result


def update_key_statuses(key_status: Dict[str, str], guess: str, statuses: List[str]) -> Dict[str, str]:
    new = dict(key_status)
    for ch, stt in zip(guess, statuses):
        prev = new.get(ch, "unused")
        if PRIORITY[stt] > PRIORITY[prev]:
            new[ch] = stt
    return new


def tile_color(status: str) -> str:
    if status == "correct":
        return "#6AAA64"
    if status == "present":
        return "#C9B458"
    if status == "absent":
        return "#787C7E"
    return "rgba(255,255,255,0.95)"


def render_board(guesses: List[str], feedback: List[List[str]], current: str, game_over: bool):
    """Always render as HTML (never as raw text)."""
    rows_html = []
    for r in range(MAX_GUESSES):
        if r < len(guesses):
            word = guesses[r]
            statuses = feedback[r]
            tiles = []
            for i in range(WORD_LENGTH):
                ch = word[i]
                stt = statuses[i]
                bg = tile_color(stt)
                tiles.append(
                    f'<div class="tile filled" style="background:{bg}; border-color:{bg}; color:#fff;">{ch}</div>'
                )
            rows_html.append(f'<div class="row">{"".join(tiles)}</div>')

        elif r == len(guesses) and not game_over:
            tiles = []
            for i in range(WORD_LENGTH):
                ch = current[i] if i < len(current) else ""
                filled = "filled" if ch else ""
                tiles.append(f'<div class="tile {filled}">{ch}</div>')
            rows_html.append(f'<div class="row">{"".join(tiles)}</div>')

        else:
            tiles = ['<div class="tile"></div>' for _ in range(WORD_LENGTH)]
            rows_html.append(f'<div class="row">{"".join(tiles)}</div>')

    html = f'<div class="board">{"".join(rows_html)}</div>'
    st.markdown(html, unsafe_allow_html=True)


def share_grid(feedback: List[List[str]]) -> str:
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


def wkey(name: str) -> str:
    return f"wordle::{name}"


def init_wordle_state():
    if wkey("mode") not in st.session_state:
        st.session_state[wkey("mode")] = "Daily"
    if wkey("answer") not in st.session_state:
        idx = stable_daily_index(seed="streamlit-wordle-like", n=len(SOLUTION_WORDS))
        st.session_state[wkey("answer")] = SOLUTION_WORDS[idx]
    if wkey("guesses") not in st.session_state:
        st.session_state[wkey("guesses")] = []
    if wkey("feedback") not in st.session_state:
        st.session_state[wkey("feedback")] = []
    if wkey("current") not in st.session_state:
        st.session_state[wkey("current")] = ""
    if wkey("key_status") not in st.session_state:
        st.session_state[wkey("key_status")] = {}
    if wkey("game_over") not in st.session_state:
        st.session_state[wkey("game_over")] = False
    if wkey("won") not in st.session_state:
        st.session_state[wkey("won")] = False
    if wkey("text_rev") not in st.session_state:
        st.session_state[wkey("text_rev")] = 0
    if wkey("error") not in st.session_state:
        st.session_state[wkey("error")] = ""
    if wkey("strict") not in st.session_state:
        st.session_state[wkey("strict")] = False


def reset_wordle(random_word: bool):
    st.session_state[wkey("answer")] = (
        random.choice(SOLUTION_WORDS)
        if random_word
        else SOLUTION_WORDS[stable_daily_index(seed="streamlit-wordle-like", n=len(SOLUTION_WORDS))]
    )
    st.session_state[wkey("guesses")] = []
    st.session_state[wkey("feedback")] = []
    st.session_state[wkey("current")] = ""
    st.session_state[wkey("key_status")] = {}
    st.session_state[wkey("game_over")] = False
    st.session_state[wkey("won")] = False
    st.session_state[wkey("error")] = ""
    st.session_state[wkey("text_rev")] += 1


def wordle_commit_guess():
    if st.session_state[wkey("game_over")]:
        return

    strict = st.session_state[wkey("strict")]
    guess = st.session_state[wkey("current")].upper().strip()

    if len(guess) != WORD_LENGTH:
        st.session_state[wkey("error")] = "Not enough letters."
        return
    if not guess.isalpha():
        st.session_state[wkey("error")] = "Only letters A–Z."
        return
    if strict and guess not in VALID_GUESSES:
        st.session_state[wkey("error")] = "Not in word list (strict mode)."
        return

    st.session_state[wkey("error")] = ""
    answer = st.session_state[wkey("answer")]
    statuses = evaluate_guess(guess, answer)

    st.session_state[wkey("guesses")].append(guess)
    st.session_state[wkey("feedback")].append(statuses)
    st.session_state[wkey("key_status")] = update_key_statuses(
        st.session_state[wkey("key_status")], guess, statuses
    )

    # lock the row by clearing current immediately
    st.session_state[wkey("current")] = ""
    st.session_state[wkey("text_rev")] += 1

    if guess == answer:
        st.session_state[wkey("game_over")] = True
        st.session_state[wkey("won")] = True
    elif len(st.session_state[wkey("guesses")]) >= MAX_GUESSES:
        st.session_state[wkey("game_over")] = True
        st.session_state[wkey("won")] = False


def wordle_handle_keypress(key: str):
    if st.session_state[wkey("game_over")]:
        return

    cur = st.session_state[wkey("current")]

    if key == "ENTER":
        wordle_commit_guess()
        return
    if key == "⌫":
        st.session_state[wkey("current")] = cur[:-1]
        st.session_state[wkey("text_rev")] += 1
        return
    if len(key) == 1 and key.isalpha():
        if len(cur) < WORD_LENGTH:
            st.session_state[wkey("current")] = cur + key.upper()
            st.session_state[wkey("text_rev")] += 1


def render_wordle_keyboard_immediate():
    for row in KEY_ROWS:
        weights = [1.6 if k in ("ENTER", "⌫") else 1.0 for k in row]
        cols = st.columns(weights)
        for i, key in enumerate(row):
            label = "Enter" if key == "ENTER" else ("⌫" if key == "⌫" else key)
            if cols[i].button(label, key=f"{wkey('kbd')}::{key}", disabled=st.session_state[wkey("game_over")]):
                wordle_handle_keypress(key)
                st.rerun()


# =============================
# TIC TAC TOE
# =============================
def tkey(name: str) -> str:
    return f"ttt::{name}"


def init_ttt_state():
    if tkey("board") not in st.session_state:
        st.session_state[tkey("board")] = [""] * 9
    if tkey("turn") not in st.session_state:
        st.session_state[tkey("turn")] = "X"
    if tkey("winner") not in st.session_state:
        st.session_state[tkey("winner")] = ""


def ttt_check_winner(board: List[str]) -> str:
    wins = [
        (0, 1, 2), (3, 4, 5), (6, 7, 8),
        (0, 3, 6), (1, 4, 7), (2, 5, 8),
        (0, 4, 8), (2, 4, 6),
    ]
    for a, b, c in wins:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]
    if all(board):
        return "DRAW"
    return ""


def ttt_move(idx: int):
    if st.session_state[tkey("winner")]:
        return
    board = st.session_state[tkey("board")]
    if board[idx]:
        return
    board[idx] = st.session_state[tkey("turn")]
    w = ttt_check_winner(board)
    st.session_state[tkey("winner")] = w
    if not w:
        st.session_state[tkey("turn")] = "O" if st.session_state[tkey("turn")] == "X" else "X"


def ttt_reset():
    st.session_state[tkey("board")] = [""] * 9
    st.session_state[tkey("turn")] = "X"
    st.session_state[tkey("winner")] = ""


# =============================
# NUMBER GUESS
# =============================
def nkey(name: str) -> str:
    return f"num::{name}"


def init_num_state():
    if nkey("target") not in st.session_state:
        st.session_state[nkey("target")] = random.randint(1, 100)
    if nkey("tries") not in st.session_state:
        st.session_state[nkey("tries")] = 0
    if nkey("done") not in st.session_state:
        st.session_state[nkey("done")] = False
    if nkey("msg") not in st.session_state:
        st.session_state[nkey("msg")] = "Pick a number from 1 to 100."


def num_reset():
    st.session_state[nkey("target")] = random.randint(1, 100)
    st.session_state[nkey("tries")] = 0
    st.session_state[nkey("done")] = False
    st.session_state[nkey("msg")] = "Pick a number from 1 to 100."


def num_submit(guess: int):
    if st.session_state[nkey("done")]:
        return
    st.session_state[nkey("tries")] += 1
    target = st.session_state[nkey("target")]
    if guess < target:
        st.session_state[nkey("msg")] = "Too low ⬇️"
    elif guess > target:
        st.session_state[nkey("msg")] = "Too high ⬆️"
    else:
        st.session_state[nkey("done")] = True
        st.session_state[nkey("msg")] = f"Correct ✅ You got it in {st.session_state[nkey('tries')]} tries!"


# =============================
# UI
# =============================
st.markdown(
    """
    <div class="hero">
        <div>
            <div class="hero-title">🎮 Mini Games Arcade</div>
            <div class="hero-sub">Multiple mini web-app games with a clean Streamlit UI.</div>
        </div>
        <div style="text-align:right; color:rgba(0,0,0,0.55); font-size:0.95rem;">
            <div><b>Tip:</b> Use the tabs</div>
            <div>to switch games</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

tab_wordle, tab_ttt, tab_num = st.tabs(["🟩 Word Guess", "❌⭕ Tic-Tac-Toe", "🔢 Number Guess"])

# -----------------------------
# Word Guess tab
# -----------------------------
with tab_wordle:
    init_wordle_state()

    st.markdown('<div class="card">', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns([2.0, 1.2, 1.1, 1.1], vertical_alignment="center")

    with c1:
        st.subheader("🟩 Word Guess")
        st.markdown('<div class="muted">5 letters · 6 tries</div>', unsafe_allow_html=True)

    with c2:
        mode = st.selectbox(
            "Mode",
            ["Daily", "Random"],
            index=0 if st.session_state[wkey("mode")] == "Daily" else 1,
            key=wkey("mode_select"),
        )
        st.session_state[wkey("mode")] = mode

    with c3:
        st.session_state[wkey("strict")] = st.toggle(
            "Strict list", value=st.session_state[wkey("strict")]
        )

    with c4:
        if st.button("New", use_container_width=True):
            reset_wordle(random_word=(mode == "Random"))
            st.rerun()

    # Render board in a stable container (always HTML)
    board_box = st.container()
    with board_box:
        render_board(
            st.session_state[wkey("guesses")],
            st.session_state[wkey("feedback")],
            st.session_state[wkey("current")],
            st.session_state[wkey("game_over")],
        )

    # Text input (key-swap pattern so it refreshes after on-screen keyboard presses)
    rev = st.session_state[wkey("text_rev")]
    text_key = f"{wkey('typed')}::{rev}"
    typed = st.text_input(
        "Type a guess",
        value=st.session_state[wkey("current")],
        key=text_key,
        max_chars=WORD_LENGTH,
        placeholder="Type 5 letters…",
        label_visibility="collapsed",
        disabled=st.session_state[wkey("game_over")],
    )

    typed_up = (typed or "").upper()[:WORD_LENGTH]
    if typed_up != st.session_state[wkey("current")]:
        st.session_state[wkey("current")] = typed_up
        st.session_state[wkey("error")] = ""

    if st.session_state[wkey("error")]:
        st.warning(st.session_state[wkey("error")])

    b1, b2, b3 = st.columns([1, 1, 1])
    with b1:
        if st.button("Enter ↵", use_container_width=True, disabled=st.session_state[wkey("game_over")]):
            wordle_commit_guess()
            st.rerun()
    with b2:
        if st.button("Backspace", use_container_width=True, disabled=st.session_state[wkey("game_over")]):
            wordle_handle_keypress("⌫")
            st.rerun()
    with b3:
        if st.button("Clear", use_container_width=True, disabled=st.session_state[wkey("game_over")]):
            st.session_state[wkey("current")] = ""
            st.session_state[wkey("error")] = ""
            st.session_state[wkey("text_rev")] += 1
            st.rerun()

    render_wordle_keyboard_immediate()

    st.markdown("---")
    if st.session_state[wkey("game_over")]:
        tries = len(st.session_state[wkey("guesses")])
        if st.session_state[wkey("won")]:
            st.success(f"Solved in {tries}/{MAX_GUESSES}!")
        else:
            st.error(f"Out of tries. Answer: **{st.session_state[wkey('answer')]}**")
        st.text_area("Share", value=share_grid(st.session_state[wkey("feedback")]), height=140)

    st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------
# Tic Tac Toe tab
# -----------------------------
with tab_ttt:
    init_ttt_state()

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("❌⭕ Tic-Tac-Toe")
    st.markdown('<div class="muted">Quick 2-player game on the same screen.</div>', unsafe_allow_html=True)

    left, right = st.columns([2, 1])
    with left:
        w = st.session_state[tkey("winner")]
        if w == "DRAW":
            st.info("It’s a draw.")
        elif w:
            st.success(f"Winner: {w}")
        else:
            st.write(f"Turn: **{st.session_state[tkey('turn')]}**")
    with right:
        if st.button("Reset", use_container_width=True):
            ttt_reset()
            st.rerun()

    st.markdown('<div class="ttt">', unsafe_allow_html=True)
    board = st.session_state[tkey("board")]
    for i in range(9):
        label = board[i] if board[i] else " "
        if st.button(label, key=f"{tkey('cell')}::{i}", disabled=bool(st.session_state[tkey("winner")])):
            ttt_move(i)
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------
# Number Guess tab
# -----------------------------
with tab_num:
    init_num_state()

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🔢 Number Guess")
    st.markdown('<div class="muted">Try to find the secret number between 1 and 100.</div>', unsafe_allow_html=True)

    colA, colB = st.columns([2, 1])
    with colA:
        st.write(st.session_state[nkey("msg")])
        st.write(f"Tries: **{st.session_state[nkey('tries')]}**")
    with colB:
        if st.button("New round", use_container_width=True):
            num_reset()
            st.rerun()

    guess = st.number_input(
        "Your guess",
        min_value=1,
        max_value=100,
        value=50,
        step=1,
        disabled=st.session_state[nkey("done")],
        label_visibility="collapsed",
        key=nkey("guess_input"),
    )

    if st.button("Submit", use_container_width=True, disabled=st.session_state[nkey("done")]):
        num_submit(int(guess))
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 🎛️ Arcade Settings")
    st.caption("Add new tabs for more games anytime.")
    st.divider()
    st.caption("Made with Streamlit ✨")
