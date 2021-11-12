from blessed import Terminal

def interface_clear(term):
    """
    Clears the terminal and sets location to home (0,0) -
    as suggested at:
    https://blessed.readthedocs.io/en/stable/location.html
    """
    print(term.home + term.clear, end='')

if __name__ == "__main__":
    term = Terminal()

    interface_clear(term)
    print(term.blue('this is the top'))
    print(term.move_y(term.height // 2) + term.black_on_darkkhaki(term.center('this is the middle')))
    print(term.home + term.move_down(term.height) + 'this is the bottom', end='')

    with term.cbreak(), term.hidden_cursor():
        while True:
            inp = term.inkey()
            print(
                term.home + term.move_down(term.height-3) + term.clear_eol +
                'You pressed ' + term.bold(repr(inp))
                )
