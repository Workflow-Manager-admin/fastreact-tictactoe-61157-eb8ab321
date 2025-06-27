from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Literal, List
from enum import Enum

# App and CORS Setup with OpenAPI metadata
app = FastAPI(
    title="Tic Tac Toe Backend API",
    description=(
        "A RESTful API backend for a Tic Tac Toe game. Provides endpoints to "
        "start a new game, get the current game state, make a move, and restart "
        "the game. Game state is managed in-memory for a single ongoing game. "
        "All responses are documented for frontend use."
    ),
    version="1.0.0",
    openapi_tags=[
        {"name": "Game", "description": "Endpoints for managing the Tic Tac Toe game state and moves."}
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -- Game Logic and In-Memory State Management --

class Player(str, Enum):
    X = "X"
    O_ = "O"  # Rename to O_ to avoid ambiguous variable name 'O'


EMPTY_CELL = ""


class MoveRequest(BaseModel):
    """Request to make a move"""
    row: int = Field(
        ...,
        ge=0, le=2,
        description="Row index (0-2)"
    )
    col: int = Field(
        ...,
        ge=0, le=2,
        description="Column index (0-2)"
    )


class RestartRequest(BaseModel):
    """Optional payload for restart endpoint (future use)"""
    pass


class GameStateResponse(BaseModel):
    """Structure of the game state response"""
    board: List[List[str]] = Field(
        ...,
        description=(
            "Current 3x3 Tic Tac Toe board as list of lists. "
            "Each cell is '', 'X', or 'O'."
        ),
    )
    current_player: Player = Field(
        ...,
        description="Player whose turn it is: 'X' or 'O'."
    )
    winner: Optional[Player] = Field(
        None,
        description="Winner: 'X' or 'O', or null if no winner yet."
    )
    draw: bool = Field(
        ...,
        description="True if the game is a draw."
    )
    status: Literal["playing", "won", "draw"] = Field(
        ...,
        description="Game status: 'playing', 'won', or 'draw'."
    )


# Single in-memory game state


class InMemoryGame:
    def __init__(self):
        self._new_game()

    def _new_game(self):
        self.board = [[EMPTY_CELL for _ in range(3)] for _ in range(3)]
        self.current_player = Player.X
        self.winner = None
        self.draw = False
        self.status = "playing"

    def get_state(self):
        return {
            "board": self.board,
            "current_player": self.current_player,
            "winner": self.winner,
            "draw": self.draw,
            "status": self.status,
        }

    def make_move(self, row: int, col: int):
        if self.status != "playing":
            raise ValueError("Game is already over.")

        if self.board[row][col] != EMPTY_CELL:
            raise ValueError("Cell is already filled.")

        self.board[row][col] = self.current_player.value
        self._update_game_status()
        # Switch player if game is not over
        if self.status == "playing":
            self.current_player = (
                Player.O_ if self.current_player == Player.X else Player.X
            )

    def _update_game_status(self):
        # Check win for current player
        lines = []

        # rows, columns
        lines.extend(self.board)
        lines.extend([[self.board[r][c] for r in range(3)] for c in range(3)])
        # diagonals
        lines.append([self.board[i][i] for i in range(3)])
        lines.append([self.board[i][2 - i] for i in range(3)])

        for line in lines:
            if all(cell == self.current_player.value for cell in line):
                self.winner = self.current_player
                self.status = "won"
                return

        # Draw: board full and no winner
        if all(cell != EMPTY_CELL for row in self.board for cell in row):
            self.draw = True
            self.status = "draw"

    def restart(self):
        self._new_game()


# Initialize the game
game = InMemoryGame()

# -- API Endpoints --

# PUBLIC_INTERFACE


@app.get("/", tags=["Game"])
def health_check():
    """Health check endpoint."""
    return {"message": "Healthy"}


# PUBLIC_INTERFACE
@app.post(
    "/game/start",
    response_model=GameStateResponse,
    summary="Start a new game",
    tags=["Game"],
    responses={
        200: {
            "description": (
                "New game started. Returns the initial empty board and game state."
            ),
            "content": {
                "application/json": {
                    "example": {
                        "board": [["", "", ""], ["", "", ""], ["", "", ""]],
                        "current_player": "X",
                        "winner": None,
                        "draw": False,
                        "status": "playing"
                    }
                }
            }
        }
    }
)
def start_game():
    """
    Start a new Tic Tac Toe game.

    Resets the game state, clears the board, and sets the current player to 'X'.
    Returns the initial game state.
    """
    game.restart()
    return game.get_state()


# PUBLIC_INTERFACE
@app.get(
    "/game/state",
    response_model=GameStateResponse,
    summary="Get current game state",
    tags=["Game"],
    responses={
        200: {
            "description": (
                "Returns the current status of the game: board, current player, "
                "winner, draw flag, and status."
            ),
            "content": {
                "application/json": {
                    "example": {
                        "board": [["X", "O", ""], ["", "X", ""], ["O", "", ""]],
                        "current_player": "O",
                        "winner": None,
                        "draw": False,
                        "status": "playing"
                    }
                }
            }
        }
    }
)
def get_game_state():
    """
    Get the current state of the ongoing Tic Tac Toe game.

    Returns:
      - board: 3x3 game board
      - current_player: whose turn it is
      - winner: winning player or null
      - draw: True if the game is a draw
      - status: "playing", "won", or "draw"
    """
    return game.get_state()


# PUBLIC_INTERFACE
@app.post(
    "/game/move",
    response_model=GameStateResponse,
    summary="Make a move",
    tags=["Game"],
    responses={
        200: {
            "description": "Move accepted. Returns the updated game state.",
            "content": {
                "application/json": {
                    "example": {
                        "board": [["X", "", ""], ["", "", ""], ["", "", ""]],
                        "current_player": "O",
                        "winner": None,
                        "draw": False,
                        "status": "playing"
                    }
                }
            }
        },
        400: {
            "description": "Invalid move or game is already over."
        }
    }
)
def make_move(move: MoveRequest):
    """
    Make a move for the current player at the specified (row, col) position.

    Validates the move and alternates the current player after a successful move.
    If the game is over or the move is invalid, returns HTTP 400.

    Returns updated game state.
    """
    try:
        game.make_move(move.row, move.col)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return game.get_state()


# PUBLIC_INTERFACE
@app.post(
    "/game/restart",
    response_model=GameStateResponse,
    summary="Restart the current game",
    tags=["Game"],
    responses={
        200: {
            "description": (
                "Game state has been reset to start a new game."
            ),
            "content": {
                "application/json": {
                    "example": {
                        "board": [["", "", ""], ["", "", ""], ["", "", ""]],
                        "current_player": "X",
                        "winner": None,
                        "draw": False,
                        "status": "playing"
                    }
                }
            }
        }
    }
)
def restart_game():
    """
    Restart the game, resetting all state to initial values.

    Returns the initial game state.
    """
    game.restart()
    return game.get_state()
