"""Rectángulo ligero sin dependencia de pygame para colisiones en modelos."""


class Rect:
    """Rectángulo simple con las mismas propiedades esenciales que pygame.Rect."""

    def __init__(self, x, y, ancho, alto):
        self.x = int(x)
        self.y = int(y)
        self.width = int(ancho)
        self.height = int(alto)

    @property
    def left(self):
        return self.x

    @property
    def right(self):
        return self.x + self.width

    @property
    def top(self):
        return self.y

    @property
    def bottom(self):
        return self.y + self.height

    @property
    def centerx(self):
        return self.x + self.width // 2

    @property
    def centery(self):
        return self.y + self.height // 2

    @property
    def center(self):
        return (self.centerx, self.centery)

    def colliderect(self, otro):
        return (self.left < otro.right and self.right > otro.left
                and self.top < otro.bottom and self.bottom > otro.top)

    def collidepoint(self, px, py=None):
        if py is None:
            px, py = px
        return self.left <= px <= self.right and self.top <= py <= self.bottom

    def inflate(self, dx, dy):
        return Rect(self.x - dx // 2, self.y - dy // 2,
                    self.width + dx, self.height + dy)

    def inflate_ip(self, dx, dy):
        self.x -= dx // 2
        self.y -= dy // 2
        self.width += dx
        self.height += dy

    def __repr__(self):
        return f"Rect({self.x}, {self.y}, {self.width}, {self.height})"
