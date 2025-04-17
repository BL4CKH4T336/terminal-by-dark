import random
import json
import os
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import logging

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Constants
WORD_LIST = [
    "APPLE", "BRAIN", "CRANE", "DANCE", "EAGLE", 
    "FLAME", "GRADE", "HEART", "IGLOO", "JUICE",
    "KOALA", "LEMON", "MUSIC", "NIGHT", "OCEAN",
    "PEACH", "QUEEN", "RIVER", "SNAKE", "TIGER",
    "UMBRA", "VIOLA", "WATER", "XENON", "YACHT", "ZEBRA"
]
LEADERBOARD_FILE = "wordseek_leaderboard.json"
MAX_ATTEMPTS = 12

# Game states
games = {}

# Load leaderboard from file
def load_leaderboard():
    if os.path.exists(LEADERBOARD_FILE):
        with open(LEADERBOARD_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

# Save leaderboard to file
def save_leaderboard(leaderboard):
    with open(LEADERBOARD_FILE, 'w') as f:
        json.dump(leaderboard, f)

# Initialize leaderboard
leaderboard = load_leaderboard()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🌟 WordSeek Bot 🌟\n\n"
        "Commands:\n"
        "/newgame - Start new game\n"
        "/stopgame - Stop current game\n"
        "/leaderboard - Show global stats\n\n"
        "Guess 5-letter words to play!\n"
        "🟩=Correct 🟨=Wrong position 🟥=Not in word"
    )

async def new_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    
    if chat_id in games:
        await update.message.reply_text("Game in progress! Use /stopgame first.")
        return
    
    answer = random.choice(WORD_LIST)
    games[chat_id] = {
        'answer': answer,
        'history': [],
        'players': {},
        'start_time': datetime.now().isoformat()
    }
    
    await update.message.reply_text(
        f"🎮 New Game Started!\n"
        f"You have {MAX_ATTEMPTS} attempts.\n"
        f"Type any 5-letter word to begin!"
    )

async def stop_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    
    if chat_id not in games:
        await update.message.reply_text("No active game to stop!")
        return
    
    answer = games[chat_id]['answer']
    del games[chat_id]
    await update.message.reply_text(f"Game stopped! The word was: {answer}")

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not leaderboard:
        await update.message.reply_text("No games played yet!")
        return
    
    # Process leaderboard data
    sorted_users = sorted(
        leaderboard.items(),
        key=lambda x: (-x[1]['wins'], x[1]['avg_attempts'])
    )
    
    response = ["🏆 Global Leaderboard 🏆\n"]
    for i, (user_id, data) in enumerate(sorted_users[:20], 1):
        response.append(
            f"{i}. {data['name']}: "
            f"🏅{data['wins']} wins | "
            f"🔢{data['games_played']} games | "
            f"🎯{data['avg_attempts']:.1f} avg tries"
        )
    
    await update.message.reply_text('\n'.join(response))

def evaluate_guess(guess: str, answer: str) -> str:
    result = [''] * 5
    guess_letters = list(guess.upper())
    answer_letters = list(answer.upper())
    
    # Green pass
    for i in range(5):
        if guess_letters[i] == answer_letters[i]:
            result[i] = "🟩"
            answer_letters[i] = None
            guess_letters[i] = None
    
    # Yellow pass
    for i in range(5):
        if guess_letters[i] and guess_letters[i] in answer_letters:
            result[i] = "🟨"
            answer_letters[answer_letters.index(guess_letters[i])] = None
    
    # Red pass
    for i in range(5):
        if not result[i]:
            result[i] = "🟥"
    
    return ''.join(result)

def update_leaderboard(user, attempts, won):
    user_id = str(user.id)
    
    if user_id not in leaderboard:
        leaderboard[user_id] = {
            'name': user.full_name,
            'wins': 0,
            'games_played': 0,
            'total_attempts': 0,
            'avg_attempts': 0
        }
    
    leaderboard[user_id]['games_played'] += 1
    leaderboard[user_id]['total_attempts'] += attempts
    
    if won:
        leaderboard[user_id]['wins'] += 1
    
    # Calculate new average
    leaderboard[user_id]['avg_attempts'] = (
        leaderboard[user_id]['total_attempts'] / 
        leaderboard[user_id]['games_played']
    )
    
    save_leaderboard(leaderboard)

async def handle_guess(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user = update.effective_user
    guess = update.message.text.upper().strip()
    
    if chat_id not in games:
        return
    
    game = games[chat_id]
    
    # Validate input
    if len(guess) != 5 or not guess.isalpha():
        return
    
    # Check if already won
    if any(fb == "🟩🟩🟩🟩🟩" for _, fb in game['history']):
        return
    
    # Check duplicate
    if any(g == guess for g, _ in game['history']):
        await update.message.reply_text(f"You already tried {guess}!")
        return
    
    # Evaluate
    feedback = evaluate_guess(guess, game['answer'])
    game['history'].append((guess, feedback))
    
    # Track player
    if user.id not in game['players']:
        game['players'][user.id] = {'name': user.full_name, 'guesses': []}
    game['players'][user.id]['guesses'].append((guess, feedback))
    
    # Build response
    response = [f"{fb} {g}" for g, fb in game['history']]
    
    # Check game status
    if feedback == "🟩🟩🟩🟩🟩":
        attempts = len(game['history'])
        update_leaderboard(user, attempts, True)
        response.append(f"\n🎉 {user.full_name} won in {attempts} tries! 🎉")
        del games[chat_id]
    elif len(game['history']) >= MAX_ATTEMPTS:
        update_leaderboard(user, MAX_ATTEMPTS, False)
        response.append(f"\nGame over! The word was: {game['answer']}")
        del games[chat_id]
    else:
        remaining = MAX_ATTEMPTS - len(game['history'])
        response.append(f"\nAttempts left: {remaining}")
    
    await update.message.reply_text('\n'.join(response))

def main() -> None:
    application = Application.builder().token("7432835582:AAF-86sHcgKBVEtJRqb7rtWR3Kd-v3Zn5t0").build()
    
    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("newgame", new_game))
    application.add_handler(CommandHandler("stopgame", stop_game))
    application.add_handler(CommandHandler("leaderboard", show_leaderboard))
    
    # Guess handler
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex(r'^[a-zA-Z]{5}$'),
        handle_guess
    ))
    
    # Run bot
    application.run_polling()

if __name__ == '__main__':
    main()
