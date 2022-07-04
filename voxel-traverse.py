"""
Incremental grid traversal algorithm implementation in python

http://www.cse.yorku.ca/~amana/research/grid.pdf
"""


from typing import Iterator, Tuple
from math import floor, copysign
import math
import pygame


class VoxelRaycaster:
    def __init__(self, width: int, height: int) -> None:
        self._width = width
        self._height = height

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    def set_dim(self, width: int, height: int) -> None:
        self._width = width
        self._height = height
    
    def _normalize(self, x, y):
        norm = math.sqrt(x**2 + y**2)
        return x / norm, y / norm
    
    def cast(self, origin: Tuple[float, float], direction: Tuple[float, float]) -> Iterator[Tuple[int, int]]:
        x = floor(origin[0])
        y = floor(origin[1])
        yield x, y

        # NOTE: I don't think normalizing is nessecary here
        dir_x, dir_y = self._normalize(*direction)
        stepX = int(copysign(1, dir_x))
        stepY = int(copysign(1, dir_y))

        try:
            tMaxX = ((stepX + 1) // 2 - (origin[0] - x)) / dir_x
        except ZeroDivisionError:
            tMaxX = math.inf
        try:
            tMaxY = ((stepY + 1) // 2 - (origin[1] - y)) / dir_y
        except ZeroDivisionError:
            tMaxY = math.inf

        try:
            tDeltaX = stepX / dir_x
        except ZeroDivisionError:
            tDeltaX = math.inf
        try:
            tDeltaY = stepY / dir_y
        except ZeroDivisionError:
            tDeltaY = math.inf

        while True:
            if tMaxX < tMaxY:
                tMaxX += tDeltaX
                x += stepX
            else:
                tMaxY += tDeltaY
                y += stepY

            if x >= self._width or x < 0:
                break
            elif y >= self._height or y < 0:
                break

            yield x, y


class RayView:
    def __init__(self, surface: pygame.surface.Surface) -> None:
        self._display_surf = surface
        self.width, self.height = self._display_surf.get_size()

        self.x, self.y = self.width // 2, self.height // 2
        self.dx, self.dy = self.width // 2 + 100, self.height // 2 + 100
        self.radius = 5
        self.click_radius = 12
        self.start_hovered = True

    def is_hovering(self, mouse_x: int, mouse_y: int) -> bool:
        if math.dist((mouse_x, mouse_y), (self.dx, self.dy)) <= self.click_radius:
            self.start_hovered = False
            return True
        elif math.dist((mouse_x, mouse_y), (self.x, self.y)) <= self.click_radius:
            self.start_hovered = True
            return True
        return False

    def translate(self, x_change: int, y_change: int):
        if self.start_hovered:
            self.x += x_change
            self.y += y_change
        else:
            self.dx += x_change
            self.dy += y_change

    def on_loop(self):
        self.width, self.height = self._display_surf.get_size()

    def on_render(self):
        pygame.draw.line(self._display_surf, (0, 0, 0), (self.x, self.y), (self.dx, self.dy), 3)
        pygame.draw.line(self._display_surf, (255, 255, 255), (self.x, self.y), (self.dx, self.dy), 1)
        pygame.draw.circle(self._display_surf, (200, 0, 0), (self.x, self.y), self.radius)
        pygame.draw.circle(self._display_surf, (0, 0, 200), (self.dx, self.dy), self.radius)


class GridView:
    def __init__(self, surface: pygame.surface.Surface) -> None:
        self._display_surf = surface
        self.width, self.height = self._display_surf.get_size()
        self.ray_view = RayView(self._display_surf)

        self.x, self.y = 0, 0
        self.drag = False
        self.drag_ray = False
        self.cell_size = 32

        self.grid_width = self.width // self.cell_size + 1
        self.grid_height = self.height // self.cell_size + 1
        
        self.grid = VoxelRaycaster(self.grid_width, self.grid_height)

    def reset_position(self):
        self.x, self.y = 0, 0

    def reset_zoom(self):
        self.cell_size = 32

    def zoom(self, amount: int):
        self.cell_size += amount
        if self.cell_size < 16:
            self.cell_size = 16
        elif self.cell_size > 64:
            self.cell_size = 64

    def translate(self, x_change: int, y_change: int):
        self.x += x_change
        self.y += y_change

    def reset_grid(self) -> None:
        self.width, self.height = self._display_surf.get_size()
        self.grid_width = self.width // self.cell_size + 1
        self.grid_height = self.height // self.cell_size + 1
        self.grid.set_dim(self.width, self.height)

    def on_event(self, event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self.reset_position()
                self.reset_zoom()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                if not self.drag:
                    if self.ray_view.is_hovering(event.pos[0], event.pos[1]):
                        self.drag_ray = True
            elif event.button == 3:
                if not self.drag_ray:
                    self.drag = True
                    pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_SIZEALL)
            elif event.button == 4:
                self.zoom(1)
            elif event.button == 5:
                self.zoom(-1)
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.drag_ray = False
            elif event.button == 3:
                self.drag = False
                if self.ray_view.is_hovering(*event.pos):
                    pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
                else:
                    pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
        elif event.type == pygame.MOUSEMOTION:
            if self.drag:
                self.translate(*event.rel)
            elif self.drag_ray:
                self.ray_view.translate(*event.rel)
            else:
                if self.ray_view.is_hovering(event.pos[0], event.pos[1]):
                    pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
                else:
                    pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)

    def get_rel_cell_xy(self, x_pos: int, y_pos: int):
        offset_x = self.x % self.cell_size
        offset_y = self.y % self.cell_size
        cell_x = (x_pos - offset_x) / self.cell_size + int(self.x % self.cell_size != 0)
        cell_y = (y_pos - offset_y) / self.cell_size + int(self.y % self.cell_size != 0)
        return cell_x, cell_y

    def on_loop(self) -> None:
        self.reset_grid()

    def on_render(self) -> None:
        # First, we draw the grid boundaries
        offset_x = self.x % self.cell_size
        offset_y = self.y % self.cell_size

        for i in range(self.grid_width + 1):
            line_x = i * self.cell_size + offset_x
            line_y = self.cell_size * self.grid_height
            pygame.draw.line(self._display_surf, (0, 0, 0), (line_x, 0), (line_x, line_y))

        for i in range(self.grid_height + 1):
            line_y = i * self.cell_size + offset_y
            line_x = self.cell_size * self.grid_width
            pygame.draw.line(self._display_surf, (0, 0, 0), (0, line_y), (line_x, line_y))

        # Next, we draw the grid cells
        print(self.get_rel_cell_xy(self.ray_view.x, self.ray_view.y))
        voxel_raycast = self.grid.cast(
            self.get_rel_cell_xy(self.ray_view.x, self.ray_view.y),
            self.get_rel_cell_xy(self.ray_view.dx - self.ray_view.x, self.ray_view.dy - self.ray_view.y)
        )

        for x, y in voxel_raycast:
            pygame.draw.rect(
                self._display_surf, (0, 0, 0),
                pygame.Rect(
                    x * self.cell_size - (self.cell_size - offset_x) % self.cell_size,
                    y * self.cell_size - (self.cell_size - offset_y) % self.cell_size,
                    self.cell_size, self.cell_size
                )
            )

        # Finally, we draw the ray
        self.ray_view.on_render()


class App:
    def __init__(self) -> None:
        self._running = False
        self.size = self.weight, self.height = 640, 400
        self._fps_clock = pygame.time.Clock()
 
    def on_init(self) -> bool:
        pygame.init()
        self._display_surf = pygame.display.set_mode(self.size)
        self.grid_view = GridView(self._display_surf)
        return True
 
    def on_event(self, event) -> None:
        if event.type == pygame.QUIT:
            self._running = False
        else:
            self.grid_view.on_event(event)

    def on_loop(self) -> None:
        self.grid_view.on_loop()

    def on_render(self) -> None:
        self._display_surf.fill((255, 255, 255))
        self.grid_view.on_render()
        pygame.display.flip()
        self._fps_clock.tick(60)

    def on_cleanup(self) -> None:
        pygame.quit()

    def on_execute(self):
        if self.on_init():
            self._running = True
 
        while self._running:
            for event in pygame.event.get():
                self.on_event(event)
            self.on_loop()
            self.on_render()
        self.on_cleanup()

if __name__ == "__main__":
    App().on_execute()

