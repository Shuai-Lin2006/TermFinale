"""3D 场景渲染：盒/球/线/箭头/标签 + 相机；不是物理求解器。"""
from __future__ import annotations

from pathlib import Path


def render_3d(spec: dict, out: Path) -> dict | None:
    objects = spec.get("objects")
    if not isinstance(objects, list) or not objects:
        return None
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection
        import numpy as np

        cam = spec.get("camera") or {}
        fig = plt.figure(figsize=(7.2, 5.2), dpi=160)
        ax = fig.add_subplot(111, projection="3d")
        ax.set_xlabel("X"); ax.set_ylabel("Y"); ax.set_zlabel("Z")
        ax.view_init(elev=float(cam.get("elev", 20)), azim=float(cam.get("azim", 30)))
        def rotate(points, deg):
            import math
            a = math.radians(float(deg or 0)); c, s = math.cos(a), math.sin(a)
            return [(x*c - y*s, x*s + y*c, z) for x, y, z in points]
        used = 0
        for ob in objects:
            typ = str(ob.get("type") or "")
            x, y, z = float(ob.get("x", 0)), float(ob.get("y", 0)), float(ob.get("z", 0))
            color = str(ob.get("color") or "#2f6f6a")
            if typ == "box":
                w, h, d = float(ob.get("w", 1)), float(ob.get("h", 1)), float(ob.get("d", 1))
                verts = [[(x, y, z), (x+w, y, z), (x+w, y+h, z), (x, y+h, z)],
                         [(x, y, z+d), (x+w, y, z+d), (x+w, y+h, z+d), (x, y+h, z+d)],
                         [(x, y, z), (x+w, y, z), (x+w, y, z+d), (x, y, z+d)],
                         [(x, y+h, z), (x+w, y+h, z), (x+w, y+h, z+d), (x, y+h, z+d)]]
                if ob.get("rotation"):
                    verts = [[(x + rx, y + ry, z + rz)
                              for rx, ry, rz in rotate([(px - x, py - y, pz - z) for px, py, pz in face], ob["rotation"])]
                             for face in verts]
                ax.add_collection3d(Poly3DCollection(verts, facecolor=color, edgecolor="#1f2937", alpha=0.55))
                if ob.get("label"):
                    ax.text(x+w/2, y+h/2, z+d/2, str(ob["label"]), color="#111827")
            elif typ == "sphere":
                r = float(ob.get("r", 0.5))
                u, v = np.mgrid[0:2*np.pi:24j, 0:np.pi:12j]
                ax.plot_surface(x + r*np.cos(u)*np.sin(v), y + r*np.sin(u)*np.sin(v), z + r*np.cos(v),
                                color=color, alpha=0.55, linewidth=0)
            elif typ == "cylinder":
                r, h = float(ob.get("r", 0.4)), float(ob.get("h", 1.0))
                u, v = np.mgrid[0:2*np.pi:24j, 0:2:2j]
                ax.plot_surface(x + r*np.cos(u), y + r*np.sin(u), z + h*v, color=color, alpha=0.55, linewidth=0)
                if ob.get("label"):
                    ax.text(x, y, z+h+0.1, str(ob["label"]), color="#111827")
            elif typ == "plane":
                w, d = float(ob.get("w", 2)), float(ob.get("d", 2))
                verts = [[(x, y, z), (x+w, y, z), (x+w, y+d, z), (x, y+d, z)]]
                ax.add_collection3d(Poly3DCollection(verts, facecolor=color, edgecolor="#1f2937", alpha=0.35))
            elif typ == "ground":
                w = float(ob.get("w", 8))
                ax.plot_surface(np.array([[-w, w], [-w, w]]), np.array([[-w, -w], [w, w]]),
                                np.array([[0, 0], [0, 0]]), color=color, alpha=0.18, linewidth=0)
            elif typ == "line":
                x2, y2, z2 = float(ob.get("x2", x+1)), float(ob.get("y2", y)), float(ob.get("z2", z))
                ax.plot([x, x2], [y, y2], [z, z2], color=color, linewidth=2)
            elif typ == "arrow":
                dx, dy, dz = float(ob.get("dx", 1)), float(ob.get("dy", 0)), float(ob.get("dz", 0))
                ax.quiver(x, y, z, dx, dy, dz, color=color, arrow_length_ratio=0.15, linewidth=2)
                if ob.get("label"):
                    ax.text(x+dx, y+dy, z+dz, str(ob["label"]), color=color)
            elif typ == "label":
                ax.text(x, y, z, str(ob.get("label") or ""), color="#111827")
            else:
                continue
            used += 1
        if not used:
            return None
        ax.set_title(str(spec.get("title") or ""))
        fig.tight_layout(); out.parent.mkdir(parents=True, exist_ok=True); fig.savefig(out); plt.close(fig)
        return {"path": str(out), "layout": "3d", "elements": used, "engine": "matplotlib-3d"}
    except Exception:
        return None


def render_physics(spec: dict, out: Path) -> dict | None:
    """点质量运动学：重力 + 初速度，Euler 积分；不是碰撞/约束求解器。"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np

        p = [float(x) for x in (spec.get("position") or [0, 0, 1])]
        v = [float(x) for x in (spec.get("velocity") or [1, 1, 4])]
        g = [float(x) for x in (spec.get("gravity") or [0, 0, -9.8])]
        duration = max(0.1, float(spec.get("duration", 2.0)))
        dt = max(0.005, min(0.05, float(spec.get("dt", 0.01))))
        if len(p) != 3 or len(v) != 3 or len(g) != 3:
            return None
        xs, ys, zs = [], [], []
        t = 0.0
        while t <= duration:
            xs.append(p[0]); ys.append(p[1]); zs.append(p[2])
            for i in range(3):
                v[i] += g[i] * dt
                p[i] += v[i] * dt
            if p[2] < 0:
                p[2] = 0.0
                if v[2] < 0:
                    v[2] = 0.0
            t += dt
        fig = plt.figure(figsize=(7.2, 5.2), dpi=160)
        ax = fig.add_subplot(111, projection="3d")
        ax.plot(xs, ys, zs, color="#c0392b", lw=2.2, label="trajectory")
        ax.scatter([xs[0]], [ys[0]], [zs[0]], color="#2c3e50", label="start")
        ax.scatter([xs[-1]], [ys[-1]], [zs[-1]], color="#27ae60", label="end")
        ax.set_xlabel("X"); ax.set_ylabel("Y"); ax.set_zlabel("Z")
        ax.set_title(str(spec.get("title") or "3D kinematics (point mass)"))
        ax.legend(fontsize=8); fig.tight_layout()
        out.parent.mkdir(parents=True, exist_ok=True); fig.savefig(out); plt.close(fig)
        return {"path": str(out), "layout": "physics3d", "elements": len(xs),
                "engine": "physics3d-euler", "duration": duration, "dt": dt,
                "note": "点质量运动学，无碰撞/约束"}
    except Exception:
        return None


def render_mujoco(spec: dict, out: Path) -> dict | None:
    """MuJoCo 刚体自由落体/抛体：真实碰撞地面；只支持单自由刚体盒。"""
    try:
        import mujoco
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        if spec.get("bodies"):
            bodies = spec["bodies"]
            parts = []
            for i, b in enumerate(bodies):
                b = dict(b); b.setdefault("name", f"b{i}")
                p0 = [float(x) for x in (b.get("position") or [0, 0, 1])]
                sz = [float(x) for x in (b.get("size") or [0.2, 0.2, 0.2])]
                parts.append(f'<body name="{b["name"]}" pos="{p0[0]} {p0[1]} {p0[2]}"><freejoint/>'
                             f'<geom type="box" size="{sz[0]} {sz[1]} {sz[2]}" rgba=".2 .55 .55 .9"/></body>')
            gv = spec.get("gravity") or [0,0,-9.8]; xml = (f'<mujoco><option gravity="{gv[0]} {gv[1]} {gv[2]}"/>'
                   f'<worldbody><geom type="plane" size="8 8 .1" rgba=".9 .9 .9 1"/>{"".join(parts)}</worldbody></mujoco>')
            m = mujoco.MjModel.from_xml_string(xml); d = mujoco.MjData(m)
            traj = {b["name"]: [] for b in bodies}
            for _ in range(int(float(spec.get("duration", 1.0)) / float(spec.get("dt", 0.002)))):
                mujoco.mj_step(m, d)
                for b in bodies:
                    bid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, b["name"])
                    traj[b["name"]].append(tuple(float(x) for x in d.xpos[bid]))
            fig = plt.figure(figsize=(7.2, 5.2), dpi=160); ax = fig.add_subplot(111, projection="3d")
            for name, pts in traj.items():
                ax.plot([p[0] for p in pts], [p[1] for p in pts], [p[2] for p in pts], lw=2, label=name)
            ax.set_xlabel("X"); ax.set_ylabel("Y"); ax.set_zlabel("Z"); ax.legend(fontsize=8)
            ax.set_title(str(spec.get("title") or "MuJoCo multi-body")); fig.tight_layout()
            out.parent.mkdir(parents=True, exist_ok=True); fig.savefig(out); plt.close(fig)
            return {"path": str(out), "layout": "mujoco", "elements": len(bodies), "engine": "mujoco-multi"}
        pos = [float(x) for x in (spec.get("position") or [0, 0, 1.0])]
        size = [float(x) for x in (spec.get("size") or [0.2, 0.2, 0.2])]
        grav = [float(x) for x in (spec.get("gravity") or [0, 0, -9.8])]
        duration = max(0.1, float(spec.get("duration", 1.2)))
        dt = max(0.0005, min(0.01, float(spec.get("dt", 0.002))))
        joint = str(spec.get("joint") or "free")
        if joint == "hinge":
            body = (f'<body pos="{pos[0]} {pos[1]} {pos[2]}"><joint type="hinge" axis="0 0 1"/>'
                    f'<geom type="box" size="{size[0]} {size[1]} {size[2]}" rgba=".2 .55 .55 .9"/></body>')
        else:
            body = (f'<body pos="{pos[0]} {pos[1]} {pos[2]}"><freejoint/>'
                    f'<geom type="box" size="{size[0]} {size[1]} {size[2]}" rgba=".2 .55 .55 .9"/></body>')
        xml = (f'<mujoco><option gravity="{grav[0]} {grav[1]} {grav[2]}"/>'
               f'<worldbody><geom type="plane" size="8 8 .1" rgba=".9 .9 .9 1"/>{body}</worldbody></mujoco>')
        m = mujoco.MjModel.from_xml_string(xml); d = mujoco.MjData(m)
        if joint == "hinge" and spec.get("qvel"):
            d.qvel[0] = float(spec["qvel"])
        xs, ys, zs = [], [], []
        for _ in range(int(duration / dt)):
            mujoco.mj_step(m, d)
            if m.nq >= 3:
                xs.append(float(d.qpos[0])); ys.append(float(d.qpos[1])); zs.append(float(d.qpos[2]))
            else:
                xs.append(float(d.qpos[0])); ys.append(0.0); zs.append(0.0)
        fig = plt.figure(figsize=(7.2, 5.2), dpi=160)
        ax = fig.add_subplot(111, projection="3d")
        ax.plot(xs, ys, zs, color="#c0392b", lw=2, label="COM")
        ax.scatter([xs[0]], [ys[0]], [zs[0]], color="#2c3e50", label="start")
        ax.scatter([xs[-1]], [ys[-1]], [zs[-1]], color="#27ae60", label="end")
        ax.set_xlabel("X"); ax.set_ylabel("Y"); ax.set_zlabel("Z")
        ax.set_title(str(spec.get("title") or "MuJoCo rigid body"))
        ax.legend(fontsize=8); fig.tight_layout()
        out.parent.mkdir(parents=True, exist_ok=True); fig.savefig(out); plt.close(fig)
        return {"path": str(out), "layout": "mujoco", "elements": len(xs), "engine": "mujoco",
                "note": "MuJoCo 单刚体；碰撞地面"}
    except Exception:
        return None
