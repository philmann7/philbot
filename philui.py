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
        total_height = term.height
        section_height = total_height // num_sections
        return (section_height * sec for sec in range(num_sections))

def interface_clear(term):
    """
    Clears the terminal and sets location to home (0,0) - (top left)
    as suggested at:
    https://blessed.readthedocs.io/en/stable/location.html
    """
    print(term.home + term.clear, end='')

def main():
    pass

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
