# Saved maps (local)

3D point clouds from FAST-LIO (`map_save` service or exit with `pcd_save_en: true`).

Default save path in config: `/tmp/fast_lio_map.pcd`

```bash
mkdir -p maps
cp /tmp/fast_lio_map.pcd maps/my_map.pcd
```

Example: `mi_mapa_sim.pcd` (FAST-LIO sim run).

**3D localization** — load directly (no offline preprocessing):

```bash
ros2 launch bot_mapping fast_lio_localization.launch.py use_sim_time:=true \
  pcd_map_path:=$(pwd)/maps/mi_mapa_sim.pcd
```

Full workflow: root `README.md` (Part 1 mapping, Part 2 localization).
