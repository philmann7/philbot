"""
A module for managing the text UI of philbot.
"""
from textwrap import wrap
from ema import CloudColor

class PhilbotUI:
    """The main class from which the UI of philbot."""
    def __init__(self, term):
        """
        Initializer for the philbot UI class.
        Should take terminal from blessed.

        self.messages is a list that should contain any messages
        (error messages, account activity) to be displayed at the bottom.
        """
        self.term = term
        self.messages = []

    @property
    def section_heights(self, num_sections=3):
        """
        Return the y-height of each section, calculated with the current terminal height.
        Defaults to three sections.
        """
        total_height = self.term.height
        section_height = total_height // num_sections
        return (section_height * sec for sec in range(num_sections))

    def interface_clear(self):
        """
        Clears the terminal and sets location to home (0,0) - (top left)
        as suggested at:
        https://blessed.readthedocs.io/en/stable/location.html
        """
        print(self.term.home + self.term.clear, end='')

    def dispatch_display(self, msg_handler, clouds, positions):
        """
        Dispatches to class specific display funcs.
        """
        self.interface_clear()
        top_height, middle_height, bottom_height = self.section_heights

        self.display_top(msg_handler, clouds, top_height)
        self.display_middle(positions, middle_height)
        self.display_bottom(bottom_height,)

    def display_top(self, msg_handler, clouds, top_height):
        """
        Printing to the top section of the terminal.
        Includes price info for tracked symbols, along with their
        moving averages and EMA cloud information.
        """
        for symbol in {"SPY"}:  # To be changed for handling multiple symbols.
            try:
                last_price = float(msg_handler.last_messages[symbol]["LAST_PRICE"])
                last_price = f'{last_price:.2f}'
            except KeyError:
                last_price = "..."
            print(self.term.move_y(top_height) + f"{symbol} Last Price: {last_price}")

            cloud = clouds[symbol]
            color, location = cloud.status
            terminal_color = self.term.black_on_green if color == CloudColor.GREEN else self.term.white_on_red
            print(terminal_color + f"Short EMA: {cloud.short_ema:.2f}")
            print(terminal_color + f"Long EMA: {cloud.long_ema:.2f}")
            print(terminal_color + f"Price relative to cloud: {location.value}; Cloud color: {color.value}" + self.term.normal)

    def display_middle(self, positions, middle_height):
        """
        Print to the middle section of the terminal.
        Prints position information.
        """
        for position in positions:
            print(self.term.move_y(middle_height) + self.term.white_on_blue, end='')
            print(f"Contract: {position.contract}")
            print(f"Net position {position.net_pos}")
            print(f"Stop: {position.stop}      Take profit: {position.take_profit:.2f}")
            print(f"Opened on signal: {position.state}")
            for order in position.associated_orders:
                print(order)
            print(self.term.normal)

    def display_bottom(self, bottom_height,):
        """
        Print to bottom section of terminal.
        Streams messages and events like sent orders or errors.
        Add strings to self.messages to display them here.
        """
        section_height = abs(self.term.height - bottom_height)
        print(self.term.move_y(self.term.height-1))
        line_count = 0
        for message in reversed(self.messages):
            message = str(message)
            lines = reversed(wrap(message, width=self.term.width))
            while lines and line_count < section_height:
                print(next(lines) + self.term.move_up, end='')
                line_count += 1


if __name__ == '__main__':
    pass
