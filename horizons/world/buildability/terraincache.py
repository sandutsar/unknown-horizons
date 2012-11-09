# ###################################################
# Copyright (C) 2012 The Unknown Horizons Team
# team@unknown-horizons.org
# This file is part of Unknown Horizons.
#
# Unknown Horizons is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the
# Free Software Foundation, Inc.,
# 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
# ###################################################

from horizons.constants import BUILDINGS
from horizons.util.shapes.rect import Rect

class TerrainRequirement:
	LAND = 1
	LAND_AND_COAST = 2
	LAND_AND_COAST_NEAR_SEA = 3

class TerrainBuildabilityCache(object):
	sizes = [(1, 1), (2, 2), (2, 3), (2, 4), (3, 3), (4, 4), (6, 6)]
	sea_radius = 3
	_deposits = [BUILDINGS.CLAY_DEPOSIT, BUILDINGS.MOUNTAIN]
	_mines = [BUILDINGS.CLAY_PIT, BUILDINGS.IRON_MINE]

	def __init__(self, island):
		super(TerrainBuildabilityCache, self).__init__()
		self._island = island
		self._land = None
		self._coast = None
		self.land_or_coast = None
		self.cache = None
		self.create_cache()

	def _init_land_and_coast(self):
		land = set()
		coast = set()

		for coords, tile in self._island.ground_map.iteritems():
			if tile.object:
				# exclude tiles with resource deposits and mines
				if tile.object.id in self._deposits or tile.object.id in self._mines:
					continue

			if 'constructible' in tile.classes:
				land.add(coords)
			elif 'coastline' in tile.classes:
				coast.add(coords)

		self._land = land
		self._coast = coast
		self.land_or_coast = land.union(coast)

	def _init_rows(self):
		# these dicts show whether there is a constructible and/or coastline tile in a row
		# of 2 or 3 tiles starting from the coords and going right
		# both are in the format {(x, y): (has land, has coast), ...}
		row2 = {}
		row3 = {}

		land = self._land
		coast = self._coast
		land_or_coast = self.land_or_coast

		for (x, y) in self.land_or_coast:
			if (x + 1, y) not in land_or_coast:
				continue

			has_land = (x, y) in land or (x + 1, y) in land
			has_coast = (x, y) in coast or (x + 1, y) in coast
			row2[(x, y)] = (has_land, has_coast)
			if (x + 2, y) not in land_or_coast:
				continue

			has_land = has_land or (x + 2, y) in land
			has_coast = has_coast or (x + 2, y) in coast
			row3[(x, y)] = (has_land, has_coast)

		self.row2 = row2
		self.row3 = row3

	def _init_squares(self):
		self._init_rows()
		row2 = self.row2
		row3 = self.row3

		sq2 = {}
		for coords in row2:
			coords2 = (coords[0], coords[1] + 1)
			if coords2 in row2:
				has_land = row2[coords][0] or row2[coords2][0]
				has_coast = row2[coords][1] or row2[coords2][1]
				sq2[coords] = (has_land, has_coast)

		sq3 = {}
		for coords in row3:
			coords2 = (coords[0], coords[1] + 1)
			coords3 = (coords[0], coords[1] + 2)
			if coords2 in row3 and coords3 in row3:
				has_land = row3[coords][0] or row3[coords2][0] or row3[coords3][0]
				has_coast = row3[coords][1] or row3[coords2][1] or row3[coords3][1]
				sq3[coords] = (has_land, has_coast)

		self.sq2 = sq2
		self.sq3 = sq3

	def create_cache(self):
		self._init_land_and_coast()

		land = {}
		land_and_coast = {}

		land[(1, 1)] = self._land
		for size in self.sizes:
			if size != (1, 1):
				land[size] = set()
				if size[0] != size[1]:
					land[(size[1], size[0])] = set()

		for size in [(2, 2), (3, 3)]:
			land_and_coast[size] = set()

		self._init_squares()

		sq2 = self.sq2
		for coords, (has_land, has_coast) in sq2.iteritems():
			x, y = coords
			if has_land and has_coast:
				# handle 2x2 coastal buildings
				land_and_coast[(2, 2)].add(coords)
			elif has_land and not has_coast:
				# handle 2x2, 2x3, and 2x4 land buildings
				land[(2, 2)].add(coords)

				if (x + 2, y) in sq2 and not sq2[(x + 2, y)][1]:
					land[(3, 2)].add(coords)
					land[(4, 2)].add(coords)
				elif (x + 1, y) in sq2 and not sq2[(x + 1, y)][1]:
					land[(3, 2)].add(coords)

				if (x, y + 2) in sq2 and not sq2[(x, y + 2)][1]:
					land[(2, 3)].add(coords)
					land[(2, 4)].add(coords)
				elif (x, y + 1) in sq2 and not sq2[(x, y + 1)][1]:
					land[(2, 3)].add(coords)

		sq3 = self.sq3
		for coords, (has_land, has_coast) in sq3.iteritems():
			x, y = coords
			if has_land and has_coast:
				# handle 3x3 coastal buildings
				land_and_coast[(3, 3)].add(coords)
			elif has_land and not has_coast:
				# handle other buildings that have both sides >= 3 (3x3, 4x4, 6x6)
				land[(3, 3)].add(coords)

				if (x, y + 3) in sq3 and not sq3[(x, y + 3)][1] and (x + 3, y) in sq3 \
					    and not sq3[(x + 3, y)][1] and (x + 3, y + 3) in sq3 and not sq3[(x + 3, y + 3)][1]:
					land[(4, 4)].add(coords)
					land[(6, 6)].add(coords)
				elif (x, y + 1) in sq3 and not sq3[(x, y + 1)][1] and (x + 1, y) in sq3 \
					    and not sq3[(x + 1, y)][1] and (x + 1, y + 1) in sq3 and not sq3[(x + 1, y + 1)][1]:
					land[(4, 4)].add(coords)

		self.cache = {}
		self.cache[TerrainRequirement.LAND] = land
		self.cache[TerrainRequirement.LAND_AND_COAST] = land_and_coast

	def create_sea_cache(self):
		# currently only 3x3 buildings can require nearby sea
		coast_set = self.cache[TerrainRequirement.LAND_AND_COAST][(3, 3)]
		near_sea = set()

		nearby_coords_list = []
		base_rect = Rect.init_from_topleft_and_size(0, 0, 3, 3)
		for coords in base_rect.get_radius_coordinates(self.sea_radius):
			nearby_coords_list.append(coords)

		world = self._island.session.world
		water_bodies = world.water_body
		sea_number = world.sea_number

		for bx, by in coast_set:
			for dx, dy in nearby_coords_list:
				coords = (bx + dx, by + dy)
				if coords in water_bodies and water_bodies[coords] == sea_number:
					near_sea.add((bx, by))
					break

		self.cache[TerrainRequirement.LAND_AND_COAST_NEAR_SEA] = {}
		self.cache[TerrainRequirement.LAND_AND_COAST_NEAR_SEA][(3, 3)] = near_sea

	def get_buildability_intersection(self, terrain_type, size, *other_cache_layers):
		result = self.cache[terrain_type][size]
		for cache_layer in other_cache_layers:
			result = result.intersection(cache_layer.cache[size])
		return result
