"""
DogBrowser - Navigation History
Manages back/forward navigation for the DogBrowser terminal browser.
Part of the DogBrowser open source project (dog-browser).
"""


class DogBrowserHistory:
    """DogBrowser navigation history with back/forward support."""

    def __init__(self, max_size=500):
        self._stack = []
        self._position = -1
        self._max_size = max_size

    def push(self, url):
        if self._position >= 0 and self._position < len(self._stack) - 1:
            self._stack = self._stack[:self._position + 1]
        self._stack.append(url)
        if len(self._stack) > self._max_size:
            self._stack.pop(0)
        self._position = len(self._stack) - 1

    def back(self):
        if self._position > 0:
            self._position -= 1
            return self._stack[self._position]
        return None

    def forward(self):
        if self._position < len(self._stack) - 1:
            self._position += 1
            return self._stack[self._position]
        return None

    def current(self):
        if 0 <= self._position < len(self._stack):
            return self._stack[self._position]
        return None

    def can_go_back(self):
        return self._position > 0

    def can_go_forward(self):
        return self._position < len(self._stack) - 1

    def get_all(self):
        return list(self._stack)

    def clear(self):
        self._stack = []
        self._position = -1
