"""
A module for managing the text UI of philbot.
"""
from blessed import Terminal

class PhilbotUI:
    """The main class from which the UI of philbot."""
    def __init__(self, term):
        """
        Initializer for the philbot UI class.
        Should take terminal from blessed.
        """
        self.term = term

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
        top_height, middle_height, bottom_height = self.section_heights()

        self.display_top(msg_handler, clouds, top_height)
        self.display_middle(positions, middle_height)
        self.display_bottom(bottom_height)

    def display_top(self, msg_handler, clouds, top_height):
        """
        Printing to the top section of the terminal.
        Includes price info for tracked symbols, along with their
        moving averages and EMA cloud information.
        """
        for symbol in {"SPY"}:  # To be changed for handling multiple symbols.
            last_price = msg_handler.last_messages[symbol]["LAST_PRICE"]
            print(self.term.move_y(top_height) + f"{symbol} Last Price: {last_price}")

            cloud = clouds[symbol]
            color, location = cloud.status
            terminal_color = self.term.black_on_green if color == CloudColor.GREEN else self.term.white_on_red
            print(terminal_color + f"Short EMA: {cloud.short_ema}")
            print(terminal_color + f"Long EMA: {cloud.long_ema}")
            print(terminal_color + f"Price relative to cloud: {location}; cloud color: {color}" + self.term.normal)

    def display_middle(self, positions, middle_height):
        """
        Print to the middle section of the terminal.
        Prints position information.
        """
        for position in positions:
            print(self.term.move_y(middle_height) + self.term.white_on_blue, end='')
            print(f"Contract: {position.contract}")
            print(f"Net position {position.net_pos}")
            print(f"Stop: {self.stop}      Take profit: {self.take_profit}")
            print(f"Opened on signal: {position.state}")
            for order in position.associated_orders:
                print(order)
            print(self.term.normal)

    def display_bottom(self, bottom_height):
        """
        Print to bottom section of terminal.
        Streams messages and events like sent orders or errors.
        """
        for message in self.messages:
            print(message)

def main():
    """Testing the module"""
    term = Terminal()
    ui = PhilbotUI(term)
    locations = "top middle bottom".split()

    interface_clear(ui.term)
    for location, section_height in zip(locations, ui.section_heights):
        print(ui.term.move_y(section_height) + f'This is the {location} section.')

if __name__ == '__main__':
    main()

# if __name__ == "__main__":
#    term = Terminal()
#
#    interface_clear(term)
#    print(term.blue('this is the top'))
#    print(term.move_y(term.height // 2) + term.black_on_darkkhaki(term.center('this is the middle')))
#    print(term.home + term.move_down(term.height) + 'this is the bottom', end='')
#
#    with term.cbreak(), term.hidden_cursor():
#        while True:
#            inp = term.inkey()
#            print(
#                term.home + term.move_down(term.height-3) + term.clear_eol +
#                'You pressed ' + term.bold(repr(inp))
#                )
