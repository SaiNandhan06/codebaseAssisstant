class ShoppingCart:
    def __init__(self):
        self.items = []

    def add_item(self, item):
        self.items.append(item)

    def total(self):
        return sum(i.price for i in self.items)


def standalone_helper(x):
    return x * 2
