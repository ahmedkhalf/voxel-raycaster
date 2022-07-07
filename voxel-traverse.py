"""
Incremental grid traversal algorithm implementation in python

http://www.cse.yorku.ca/~amana/research/grid.pdf
"""


import math
from math import copysign, floor
from typing import Iterator, Tuple

import pygame
import pygame.freetype


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

    def cast(
        self, origin: Tuple[float, float], direction: Tuple[float, float]
    ) -> Iterator[Tuple[int, int]]:
        x = floor(origin[0])
        y = floor(origin[1])
        yield x, y

        dir_x, dir_y = direction
        stepX = int(copysign(1, dir_x))
        stepY = int(copysign(1, dir_y))
        positiveStepX = stepX > 0
        positiveStepY = stepY > 0
        justOutX = positiveStepX * self.width + stepX
        justOutY = positiveStepY * self.height + stepY

        # Unlike c, python does not implicitly set division by 0 to inf
        if dir_x != 0:
            tMaxX = (positiveStepX - (origin[0] - x)) / dir_x
            tDeltaX = stepX / dir_x
        else:
            tMaxX = math.inf
            tDeltaX = math.inf

        if dir_y != 0:
            tMaxY = (positiveStepY - (origin[1] - y)) / dir_y
            tDeltaY = stepY / dir_y
        else:
            tMaxY = math.inf
            tDeltaY = math.inf

        while True:
            if tMaxX < tMaxY:
                x += stepX
                if x == justOutX:
                    return
                tMaxX += tDeltaX
            else:
                y += stepY
                if y == justOutY:
                    return
                tMaxY += tDeltaY

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
        pygame.draw.line(
            self._display_surf, (255, 255, 255), (self.x, self.y), (self.dx, self.dy), 1
        )
        pygame.draw.circle(self._display_surf, (200, 0, 0), (self.x, self.y), self.radius)
        pygame.draw.circle(self._display_surf, (0, 0, 200), (self.dx, self.dy), self.radius)


class GridView:
    def __init__(self, surface: pygame.surface.Surface) -> None:
        self._display_surf = surface
        self.width, self.height = self._display_surf.get_size()
        self.ray_view = RayView(self._display_surf)

        # state
        self.drag = False
        self.drag_ray = False
        self.last_cursor = None

        self.x, self.y = 0, 0
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
        self.grid.set_dim(self.grid_width, self.grid_height)

    def _set_cursor(self, cursor) -> None:
        if self.last_cursor != cursor:
            pygame.mouse.set_cursor(cursor)
            self.last_cursor = cursor

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
                    self._set_cursor(pygame.SYSTEM_CURSOR_SIZEALL)
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
                    self._set_cursor(pygame.SYSTEM_CURSOR_HAND)
                else:
                    self._set_cursor(pygame.SYSTEM_CURSOR_ARROW)
        elif event.type == pygame.MOUSEMOTION:
            if self.drag:
                self.translate(*event.rel)
            elif self.drag_ray:
                self.ray_view.translate(*event.rel)
            else:
                if self.ray_view.is_hovering(event.pos[0], event.pos[1]):
                    self._set_cursor(pygame.SYSTEM_CURSOR_HAND)
                else:
                    self._set_cursor(pygame.SYSTEM_CURSOR_ARROW)

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
        start_x, start_y = self.get_rel_cell_xy(self.ray_view.x, self.ray_view.y)
        end_x, end_y = self.get_rel_cell_xy(self.ray_view.dx, self.ray_view.dy)
        voxel_raycast = self.grid.cast(
            (start_x, start_y),
            (end_x - start_x, end_y - start_y),
        )

        for x, y in voxel_raycast:
            pygame.draw.rect(
                self._display_surf,
                (0, 0, 0),
                pygame.Rect(
                    x * self.cell_size - (self.cell_size - offset_x) % self.cell_size,
                    y * self.cell_size - (self.cell_size - offset_y) % self.cell_size,
                    self.cell_size,
                    self.cell_size,
                ),
            )

        # Finally, we draw the ray
        self.ray_view.on_render()


class InfoViewUI:
    def __init__(self, surface: pygame.surface.Surface) -> None:
        self._display_surf = surface
        self.font = pygame.freetype.get_default_font()
        self._font = pygame.freetype.SysFont(self.font, 16)
        self._text = ""
        self._rendered_font = None

        self.max_text_width = 0
        self.max_text_height = 0

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, text: str):
        if text != self._text:
            self._text = text
            self._rendered_font, _ = self._font.render(text, (255, 255, 255))

    def on_render(self):
        if self._rendered_font is not None:
            self.max_text_width = max(self._rendered_font.get_width(), self.max_text_width)
            self.max_text_height = max(self._rendered_font.get_height(), self.max_text_height)
            text_rect = pygame.Rect(
                16 - 8, 16 - 8, self.max_text_width + 8 * 2, self.max_text_height + 8 * 2
            )
            pygame.draw.rect(self._display_surf, (0, 0, 0), text_rect)
            self._display_surf.blit(self._rendered_font, (16, 16))


class App:
    def __init__(self) -> None:
        self._running = False
        self.size = self.weight, self.height = 640, 400
        self._fps_clock = pygame.time.Clock()

    def on_init(self) -> bool:
        pygame.init()
        self._display_surf = pygame.display.set_mode(self.size, pygame.RESIZABLE)
        self.grid_view = GridView(self._display_surf)
        self.info_ui = InfoViewUI(self._display_surf)
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
        self.info_ui.on_render()
        pygame.display.flip()
        self._fps_clock.tick(60)
        self.info_ui.text = "FPS: " + str(self._fps_clock.get_fps())[:4]

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
