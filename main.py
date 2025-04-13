from math import pi
from random import choice, randint, random, uniform
from typing import Iterator, List, Optional

from pygame.geometry import Circle
from pygame.typing import Point, ColorLike
import pygame


BALL_COLOR = (255, 255, 255)
BALL_REFLECT_ANGLE = 5
BALL_GRAVITY = 0.275
BALL_RADIUS = 12.5

ARC_DELTA = pi / 6
ARC_SPEED_MIN = 150
ARC_SPEED_MAX = 300
ARC_STEP = 40

PARTICLE_SPEED = 0.5
PARTICLE_LIFETIME = 40
PARTICLE_AMOUNT = 200

HINT_TEXT = "Режими переключаются кнопками: 1 2 3\nРазрушение при столкновении: 4\nРегулировка скорости - колёсиком"


class Sprite:
    speed_mult = 1.0

    def __init__(self, center: Point, image: pygame.Surface) -> None:
        if image.width != image.height:
            raise Exception()

        self.__image = image.copy()
        self.__circle = Circle(center, image.width / 2)
        self.__alive = True

    @property
    def alive(self) -> bool:
        return self.__alive

    @property
    def image(self) -> pygame.Surface:
        return self.__image

    @property
    def rect(self) -> pygame.FRect:
        return self.__circle.as_frect()

    @property
    def mask(self) -> pygame.Mask:
        return pygame.mask.from_surface(self.__image)

    @property
    def circle(self) -> Circle:
        return self.__circle

    def kill(self) -> None:
        self.__alive = False

    def update(self) -> None:
        pass

    def render(self, surface: pygame.Surface) -> None:
        surface.blit(self.__image, self.rect)


class Group:
    def __init__(self) -> None:
        self.__sprites: List[Sprite] = list()

    def __iter__(self) -> Iterator[Sprite]:
        for sprite in self.__sprites:
            yield sprite

    def __len__(self) -> int:
        return len(self.__sprites)

    def __getitem__(self, key: int) -> Sprite:
        return self.__sprites[key]

    def add(self, *sprites: Sprite) -> None:
        self.__sprites.extend(sprites)

    def remove(self, *sprites: Sprite) -> None:
        [self.__sprites.remove(s) for s in sprites if s in self.__sprites]

    def update(self) -> None:
        for sprite in self.__sprites.copy():
            if sprite.alive:
                sprite.update()
            else:
                self.__sprites.remove(sprite)

    def render(self, surface: pygame.Surface) -> None:
        for sprite in self.__sprites:
            sprite.render(surface)

    def clear(self) -> None:
        self.__sprites.clear()


class Ball(Sprite):
    def __init__(self, center: Point, radius: float) -> None:
        image = pygame.Surface((radius * 2, radius * 2))
        pygame.draw.aacircle(image, BALL_COLOR, (radius, radius), radius)
        image.set_colorkey((0, 0, 0))
        super().__init__(center, image)

        self.__velocity = pygame.Vector2()

    @property
    def velocity(self) -> pygame.Vector2:
        return self.__velocity

    def reset(self, center: Point) -> None:
        self.__velocity.update(0)
        self.circle.center = center

    def reflect(self, circle: Circle) -> None:
        radius = circle.radius - self.circle.radius
        dx = circle.center[0] - self.circle.center[0]
        dy = circle.center[1] - self.circle.center[1]
        length = (dx**2 + dy**2) ** 0.5
        normal = pygame.Vector2(dx, dy).normalize()
        angle = (random() - 0.5) * BALL_REFLECT_ANGLE

        self.circle.move_ip(self.__velocity.normalize() * (radius - length))
        self.__velocity.reflect_ip(normal.rotate(angle))

    def update(self) -> None:
        self.circle.move_ip(self.__velocity * Sprite.speed_mult)
        self.__velocity.y += BALL_GRAVITY


class Arc(Sprite):
    def __init__(
        self,
        center: Point,
        radius: float,
        color: Optional[ColorLike] = None,
        angle: Optional[float] = None,
        speed: Optional[float] = None,
    ) -> None:
        if color:
            color = pygame.Color(color)
            self.__color = [color.r, color.g, color.b]
        else:
            self.__color = [randint(50, 255) for _ in range(3)]

        if speed:
            self.__speed = speed
        else:
            self.__speed = choice([1, -1]) * pi / randint(ARC_SPEED_MIN, ARC_SPEED_MAX)

        self.__angle = angle if angle else random() * 2 * pi

        image = pygame.Surface((radius * 2, radius * 2))
        pygame.draw.arc(
            image,
            self.__color,
            image.get_rect(),
            self.__angle,
            self.__angle - ARC_DELTA,
            2,
        )
        image.set_colorkey((0, 0, 0))
        super().__init__(center, image)

    @property
    def angle(self) -> float:
        return self.__angle

    @property
    def color(self) -> List[int]:
        return self.__color

    def collide_ball(self, ball: Ball) -> bool:
        radius = self.circle.radius - ball.circle.radius
        dx = self.circle.center[0] - ball.circle.center[0]
        dy = self.circle.center[1] - ball.circle.center[1]
        length = (dx**2 + dy**2) ** 0.5
        ball.circle.move_ip(ball.velocity.normalize() * (radius - length))
        return bool(pygame.sprite.collide_mask(self, ball))

    def update(self) -> None:
        self.__angle += self.__speed * Sprite.speed_mult
        self.image.fill((0, 0, 0))
        pygame.draw.arc(
            self.image,
            self.__color,
            self.image.get_rect(),
            self.__angle,
            self.__angle - ARC_DELTA,
            2,
        )


class Particle(Sprite):
    def __init__(
        self,
        center: Point,
        color: ColorLike,
        radius: float,
        velocity: Optional[pygame.Vector2] = None,
        gravity: Optional[pygame.Vector2] = None,
        lifetime: Optional[float] = None,
    ) -> None:
        self.__velocity = (
            velocity.copy()
            if velocity
            else pygame.Vector2(PARTICLE_SPEED).rotate(random() * 360)
        )
        self.__gravity = pygame.Vector2(0, 0.1) if gravity is None else gravity.copy()
        self.__lifetime = lifetime if lifetime else PARTICLE_LIFETIME
        self.__color = pygame.Color(color)
        self.__color.a = 255

        image = pygame.Surface((radius * 2, radius * 2)).convert_alpha()
        pygame.draw.aacircle(image, self.__color, (radius, radius), radius)
        image.set_colorkey((0, 0, 0))

        super().__init__(center, image)

    def update(self) -> None:
        self.circle.move_ip(self.__velocity * Sprite.speed_mult)
        self.__velocity += self.__gravity
        self.__lifetime -= Sprite.speed_mult
        self.__color.a = int(
            max(min(255 * self.__lifetime / PARTICLE_LIFETIME, 255), 0)
        )

        radius = self.circle.radius
        self.image.fill((0, 0, 0))
        pygame.draw.aacircle(self.image, self.__color, (radius, radius), radius)
        self.image.set_colorkey((0, 0, 0))

        if self.__lifetime <= 0:
            self.kill()


def random_angle_with_cut(start: float, length: float) -> float:
    if length <= 0:
        raise ValueError("Длина дуги должна быть положительной")
    if length >= 2 * pi:
        raise ValueError("Длина дуги должна быть меньше 2π")

    start = start % (2 * pi)
    end = start + length

    if end > 2 * pi:
        end_wrapped = end % (2 * pi)
        allowed_start = end_wrapped
        allowed_end = start
        total_length = allowed_end - allowed_start
        random_value = uniform(0, total_length)
        angle = allowed_start + random_value
    else:
        allowed1_length = start
        allowed2_length = 2 * pi - end
        total_length = allowed1_length + allowed2_length
        random_value = uniform(0, total_length)

        if random_value < allowed1_length:
            angle = random_value
        else:
            angle = end + (random_value - allowed1_length)

    return angle % (2 * pi)


def break_arc(arc: Arc, particles: Group, center: pygame.Vector2) -> None:
    arc.kill()

    for _ in range(PARTICLE_AMOUNT):
        theta = random_angle_with_cut(arc.angle - ARC_DELTA, ARC_DELTA)
        radius = pygame.Vector2(arc.circle.radius, 0).rotate_rad(-theta)
        particles.add(Particle(center + radius, arc.color, randint(1, 3)))


def set_mode(key: int, sprites: Group, center: pygame.Vector2) -> None:
    max_r = min(center) - 50
    color = [randint(50, 255) for _ in range(3)]
    angle = random() * 2 * pi
    speed = choice([1, -1]) * pi / randint(ARC_SPEED_MIN, ARC_SPEED_MAX)
    arcs = []

    if key == pygame.K_1:
        arcs = [Arc(center, max_r - i * ARC_STEP) for i in range(9)]
    elif key == pygame.K_2:
        arcs = [
            Arc(center, max_r - i * ARC_STEP, color, angle, speed + i / 2000)
            for i in range(9)
        ]
    elif key == pygame.K_3:
        arcs = [
            Arc(
                center,
                max_r - i * ARC_STEP,
                color,
                angle + pi * (i % 2),
                speed if i % 2 else -speed,
            )
            for i in range(9)
        ]

    sprites.add(*arcs)


def main() -> None:
    pygame.init()

    display = pygame.display.set_mode(flags=pygame.FULLSCREEN | pygame.DOUBLEBUF)
    clock = pygame.Clock()
    font = pygame.Font(None, 32)

    running = True
    center = pygame.Vector2(display.size) / 2
    destroy_on_collide = False
    particles_on_cursor = False

    ball = Ball(center, BALL_RADIUS)
    all_sprites = Group()
    particles = Group()

    all_sprites.add(
        ball, *[Arc(center, min(center) - 50 - i * ARC_STEP) for i in range(9)]
    )

    hint_image = font.render(HINT_TEXT, True, (255, 255, 255))
    hint_rect = hint_image.get_rect(topleft=(10, 10))

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                    Sprite.speed_mult = 1
                    all_sprites.clear()
                    ball.reset(center)
                    particles.clear()
                    all_sprites.add(ball)

                    set_mode(event.key, all_sprites, center)

                elif event.key == pygame.K_4:
                    destroy_on_collide = not destroy_on_collide

                elif event.key == pygame.K_9:
                    particles_on_cursor = not particles_on_cursor

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    color = [235, 113, 20]
                    particles.add(
                        *[
                            Particle(
                                pygame.mouse.get_pos(),
                                [c + randint(-20, 20) for c in color],
                                randint(2, 5),
                                pygame.Vector2((random() - 0.5) * 2, -1),
                                pygame.Vector2(0, random() / 40),
                                randint(30, 60),
                            )
                            for _ in range(40)
                        ]
                    )
                elif event.button == 2:
                    Sprite.speed_mult = 1

            elif event.type == pygame.MOUSEMOTION and particles_on_cursor:
                color = [randint(50, 255) for _ in range(3)]
                particles.add(
                    *[
                        Particle(
                            pygame.mouse.get_pos(),
                            color,
                            randint(2, 5),
                            pygame.Vector2(0, random() * 2).rotate(randint(0, 360)),
                            lifetime=randint(30, 60),
                        )
                        for _ in range(5)
                    ]
                )

            elif event.type == pygame.MOUSEWHEEL:
                Sprite.speed_mult = min(max(Sprite.speed_mult + 0.1 * event.y, 0.1), 3)

        all_sprites.update()
        particles.update()

        if len(all_sprites) > 1 and not all_sprites[-1].circle.contains(ball.circle):
            arc: Arc = all_sprites[-1]  # type: ignore

            if arc.collide_ball(ball):
                if destroy_on_collide:
                    break_arc(arc, particles, center)
                ball.reflect(arc.circle)
            else:
                break_arc(arc, particles, center)

        display.fill((0, 0, 0))
        all_sprites.render(display)
        particles.render(display)

        display.blit(hint_image, hint_rect)

        pygame.display.update()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
