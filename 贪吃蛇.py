import random
import sys
import time
from enum import Enum

from PyQt6.QtCore import QBasicTimer, QTimer, Qt
from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QBrush
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox


class Direction(Enum):
    """Enum for possible movement directions of the snake."""
    UP = 0
    DOWN = 1
    LEFT = 2
    RIGHT = 3


# Define the offsets for each direction
direction_offsets = {
    Direction.UP: (0, -1),
    Direction.DOWN: (0, 1),
    Direction.LEFT: (-1, 0),
    Direction.RIGHT: (1, 0)
}
# Determine the end direction by excluding the opposite of current_direction and target_direction
opposite_directions = {
    Direction.UP: Direction.DOWN,
    Direction.DOWN: Direction.UP,
    Direction.LEFT: Direction.RIGHT,
    Direction.RIGHT: Direction.LEFT
}


def calculate_new_direction(src_x, src_y, dest_x, dest_y, current_dir):
    """
    Calculate the new direction to move from the source to the destination.
    """
    delta_x = dest_x - src_x
    delta_y = dest_y - src_y

    horizontal_movement = abs(delta_x) > abs(delta_y)

    if horizontal_movement:
        if delta_x > 0:
            if current_dir != Direction.LEFT:
                return Direction.RIGHT
            else:
                return Direction.DOWN
        elif delta_x < 0:
            if current_dir != Direction.RIGHT:
                return Direction.LEFT
            else:
                return Direction.UP

    else:
        if delta_y > 0:
            if current_dir != Direction.UP:
                return Direction.DOWN
            else:
                return Direction.LEFT

        elif delta_y < 0:
            if current_dir != Direction.DOWN:
                return Direction.UP
            else:
                return Direction.RIGHT

    return current_dir


class Snake:
    """Class representing the snake and its behavior."""

    def __init__(self):
        self.food_position = None
        self.body_position = None
        self.ignore_body_conflict = True
        self.block_size = 50  # Size of a single snake segment
        self.scores = 0  # Player's score
        self.frame_time = 50  # Time between game updates in milliseconds
        self.height = 600  # Game area height
        self.width = 700  # Game area width
        self.init_body_position()  # Set initial position
        self.direction = Direction.RIGHT  # Initial movement direction
        self.new_food()  # Create initial food position

    def init_body_position(self):
        """Initialize snake body to start in the middle of the game area."""
        mid_x = self.width // 2
        mid_y = self.height // 2
        self.body_position = [
            (mid_x, mid_y),  # Head
            (mid_x - self.block_size, mid_y),  # Body segment
            (mid_x - 2 * self.block_size, mid_y)  # Tail segment
        ]

    def judge_game(self):
        """Check for game over conditions."""
        if self.body_position[0] in self.body_position[1:]:
            if self.ignore_body_conflict:
                return True  # Snake head collided with its body

        x, y = self.body_position[0]
        if not (0 <= x < self.width and 0 <= y < self.height):
            return True  # Snake head collided with wall

        return False

    def new_food(self):
        """Place new food in the game area, ensuring it is not on the snake."""
        # Avoid placing food on top of the snake
        while True:
            x = random.randint(0, self.width - self.block_size - 1)
            y = random.randint(0, self.height - self.block_size - 1)
            position = (x // self.block_size * self.block_size,
                        y // self.block_size * self.block_size)
            if position not in self.body_position:
                self.food_position = position
                break

    def add_body_segment(self, position):
        """Add a new segment to the snake's body."""
        self.body_position.insert(0, position)

    def move(self):
        """Move snake forward and remove the last segment."""
        new_head = self.get_next_position(self.body_position[0], self.direction)
        self.body_position.insert(0, new_head)  # New head becomes first segment
        self.body_position.pop()  # Remove last segment

    def get_next_position(self, position, direction):
        """Get the next position of the snake's head given its current position and direction."""
        x, y = position
        if direction == Direction.UP:
            return x, y - self.block_size
        elif direction == Direction.DOWN:
            return x, y + self.block_size
        elif direction == Direction.LEFT:
            return x - self.block_size, y
        elif direction == Direction.RIGHT:
            return x + self.block_size, y

    def eat(self):
        """Handle food consumption by the snake."""
        if self.food_position and self.food_position == self.body_position[0]:
            self.add_body_segment(self.food_position)
            self.scores = len(self.body_position) - 3
            self.new_food()


class SnakeGameWindow(QMainWindow):
    """Main game window for the Snake game."""

    def __init__(self):
        super().__init__()

        # Set up the game and UI elements
        self.snake = Snake()
        self.init_ui()
        self.auto_play_enabled = False
        self.auto_play_timer = QBasicTimer()
        self.auto_play_timer.start(self.snake.frame_time, self)

        # Frame rate calculation
        self.start_time = time.time()
        self.frame_count = 0
        self.fps_timer = QTimer()
        self.fps_timer.timeout.connect(self.update_status_bar)
        self.fps_timer.start(1000)

        self.setWindowTitle('Snake Game')
        self.show()

    def init_ui(self):
        """Set up the UI elements for the game."""
        self.setMinimumSize(self.snake.width, self.snake.height)
        self.setStatusTip('Use arrow keys to control the snake. Press Space for auto-play mode.')

    def update_status_bar(self):
        """Calculate frame rate and display game status."""
        current_time = time.time()
        elapsed_time = current_time - self.start_time
        frame_rate = self.frame_count / elapsed_time if elapsed_time > 0 else 0
        self.start_time = current_time
        self.frame_count = 0

        # Display the current status
        fps_str = f"FPS: {frame_rate:.2f}"
        body_conflict_str = f"Body-Conflict: {self.snake.ignore_body_conflict}"
        direction_str = f"Direction: {self.snake.direction.name}"
        score_str = f"Score: {self.snake.scores}"
        auto_str = f"Auto-play: {'ON' if self.auto_play_enabled else 'OFF'}"
        position_str = f"Snake-Position: {self.snake.body_position[0]}"
        speed_str = f"Speed: {self.snake.frame_time}"
        status = f"{speed_str} | {auto_str} | {body_conflict_str} | {score_str} | {position_str} | {fps_str} | {direction_str}"
        self.statusBar().showMessage(status)

    def paintEvent(self, e):
        """Draw the game graphics."""
        painter = QPainter(self)
        self.draw_snake(painter)
        self.draw_food(painter)

        # Increment frame count for FPS calculation
        self.frame_count += 1

    def draw_snake(self, painter):
        """Draw the snake on the board with enhanced visual effects."""
        body_position = self.snake.body_position
        block_size = self.snake.block_size

        # Drawing snake body with gradient color and transparency
        painter.setPen(Qt.PenStyle.NoPen)
        for index, (x, y) in enumerate(body_position):
            if index == 0:  # Snake head
                # Head color
                painter.setBrush(QColor(255, 0, 0))
                painter.drawRect(x, y, block_size, block_size)
                # Draw eyes
                painter.setBrush(QColor(255, 255, 255))  # White eyes
                eye_size = int(block_size / 4)
                painter.drawEllipse(x + eye_size, y + eye_size, eye_size, eye_size)
                painter.drawEllipse(x + 3 * eye_size, y + eye_size, eye_size, eye_size)
            else:
                # Gradient color for body
                gradient = QLinearGradient(x, y, x + block_size, y + block_size)
                green_component = 255 - int(255 * index / len(body_position))
                gradient.setColorAt(0, QColor(0, 255, 0, 255))
                gradient.setColorAt(1, QColor(0, green_component, 0, 100))
                painter.setBrush(QBrush(gradient))

                # Draw body segments without border
                painter.drawRect(x, y, block_size, block_size)

            # Adding random spots
            if index != 0:  # Avoid drawing on the head
                spot_color = QColor(0, 0, 0, 50)  # Black spots with some transparency
                painter.setBrush(spot_color)
                for _ in range(random.randint(0, 2)):  # Random number of spots
                    spot_x = x + random.randint(0, block_size)
                    spot_y = y + random.randint(0, block_size)
                    painter.drawEllipse(spot_x, spot_y, 2, 2)  # Small spots

    def draw_food(self, painter):
        """Draw the food on the board."""
        if self.snake.food_position:
            x, y = self.snake.food_position
            painter.setBrush(QColor(255, 255, 0))  # Yellow color for the food
            painter.drawRect(x, y, self.snake.block_size, self.snake.block_size)

    def safe_move_judge(self, target_direction):
        """ Judge if the select direction ok."""
        current_body_position = self.snake.body_position.copy()
        head_x, head_y = current_body_position[0]
        offset = direction_offsets[target_direction]
        future_head_position = (head_x + offset[0] * self.snake.block_size, head_y + offset[1] * self.snake.block_size)
        # Emulate the further step
        current_body_position.insert(0, future_head_position)  # New head becomes first segment
        current_body_position.pop()  # Remove last segment

        if future_head_position in current_body_position[1:]:
            return True  # hit the body

        for x, y in current_body_position:
            if x < 0 or x >= self.snake.width - self.snake.block_size or y < 0 or y >= self.snake.height - self.snake.block_size:
                return True  # hit the boundary

        return False

    def safe_board_judge(self, target_direction):
        """ Judge if the select direction to board ok."""
        current_body_position = self.snake.body_position.copy()
        head_x, head_y = current_body_position[0]
        offset = direction_offsets[target_direction]
        future_head_position = (head_x + offset[0] * self.snake.block_size, head_y + offset[1] * self.snake.block_size)
        # Emulate the further step
        current_body_position.insert(0, future_head_position)  # New head becomes first segment
        current_body_position.pop()  # Remove last segment

        for x, y in current_body_position:
            if x < 0 or x >= self.snake.width - self.snake.block_size or y < 0 or y >= self.snake.height - self.snake.block_size:
                return True  # hit the boundary

        return False

    def detect_direction(self):
        """Auto select the best direction."""
        food_x = self.snake.food_position[0]
        food_y = self.snake.food_position[1]
        head_x, head_y = self.snake.body_position[0]
        current_direction = self.snake.direction
        target_direction = calculate_new_direction(head_x, head_y, food_x, food_y, current_direction)
        if not self.safe_move_judge(target_direction):
            # Judge if it ok
            self.snake.direction = target_direction
        else:
            # Determine the end direction randomly from the remaining directions
            random_direction = random.choice([Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT])
            count = 0
            while self.safe_move_judge(random_direction):
                count += 1
                if count > 66:
                    if self.snake.ignore_body_conflict:
                        self.end_game()
                    else:
                        break
                random_direction = random.choice([Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT])
            if not self.snake.ignore_body_conflict:
                while self.safe_board_judge(random_direction):
                    random_direction = random.choice([Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT])
            self.snake.direction = random_direction

    def resizeEvent(self, event):
        """Handle window resizing events."""
        try:
            width = self.size().width()
            height = self.size().height()
            self.snake.height = height
            self.snake.width = width
        except Exception as e:
            print(f"Error during resizing: {e}")

    def keyPressEvent(self, event):
        """Handle keyboard input."""
        key = event.key()

        if key == Qt.Key.Key_Up and self.snake.direction != Direction.DOWN:
            self.snake.direction = Direction.UP
        elif key == Qt.Key.Key_Down and self.snake.direction != Direction.UP:
            self.snake.direction = Direction.DOWN
        elif key == Qt.Key.Key_Left and self.snake.direction != Direction.RIGHT:
            self.snake.direction = Direction.LEFT
        elif key == Qt.Key.Key_Right and self.snake.direction != Direction.LEFT:
            self.snake.direction = Direction.RIGHT
        elif key == Qt.Key.Key_R:
            self.snake = Snake()  # Reset the game
            self.auto_play_timer.stop()
            self.auto_play_timer.start(self.snake.frame_time, self)
        elif key == Qt.Key.Key_A:
            self.auto_play_timer.stop()
            self.snake.frame_time -= 2  # Acc the game
            self.auto_play_timer.start(self.snake.frame_time, self)
        elif key == Qt.Key.Key_S:
            self.auto_play_timer.stop()
            self.snake.frame_time += 2  # Slow the game
            self.auto_play_timer.start(self.snake.frame_time, self)
        elif key == Qt.Key.Key_Space:
            # Toggle auto-play mode
            self.auto_play_enabled = not self.auto_play_enabled
            self.snake.ignore_body_conflict = not self.snake.ignore_body_conflict
        elif key == Qt.Key.Key_C:
            # Toggle body-conflict mode
            self.snake.ignore_body_conflict = not self.snake.ignore_body_conflict

    def timerEvent(self, event):
        """Handle timer events for game updates."""
        if event.timerId() == self.auto_play_timer.timerId() and self.auto_play_enabled:
            # Autoplay logic (e.g., heuristic algorithm can be added here)
            self.snake.eat()
            self.detect_direction()
            self.snake.move()

            if self.snake.judge_game():
                self.end_game()
            self.update()

        if not self.auto_play_enabled:
            # Manual play: game logic goes here (the snake moves forward)
            self.snake.eat()
            self.snake.move()

            if self.snake.judge_game():
                self.end_game()
            self.update()

    def end_game(self):
        """Show a game-over message and reset the game."""
        msg_box = QMessageBox()
        msg_box.setWindowTitle('Game Over')
        msg_box.setText('Game over. Would you like to try again?')
        msg_box.addButton(QMessageBox.StandardButton.Ok)
        if msg_box.exec() == QMessageBox.StandardButton.Ok:
            self.snake = Snake()  # Reset the game
            self.auto_play_timer.stop()
            self.auto_play_timer.start(self.snake.frame_time, self)


def main():
    """Main function to start the application."""
    app = QApplication(sys.argv)
    game_window = SnakeGameWindow()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()

# nuitka --mingw64 --standalone --show-progress --show-memory --enable-plugin=pyqt6 --windows-disable-console --onefile --output-dir=nuitka_out  Snakes.py