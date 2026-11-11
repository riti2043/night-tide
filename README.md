# 🌊 Night Tide

> *A living night sea, rendered in letters and light.*

**Night Tide** is a generative ASCII-art animation of the ocean at night — written entirely in one Python file. Every character on screen is calculated from physics-inspired wave equations, Fresnel reflectance, and procedural breaker simulation. No images. No pre-rendered frames. Just math and motion.

```
    . . : ~ ~ + * ^ 0 0 1 | /
  . , : ~ + + * ^ 0 1 | | / \
. , ~ ~ + * * ^ 0 0 1 / \ - _
, ~ + * ^ 0 0 1 | / \ - _ # (
```

---

## ✨ Features

- **10-layer Gerstner wave** ocean — crests are sharp, troughs are wide, just like real deep water
- **Fresnel reflectance** — the distant sea glows silver, the near sea stays dark
- **Procedural breakers** — every wave that rolls in is unique: different size, angle, bend, and timing
- **Beach foam & swash** — white water rushes up the sand and slowly dissolves into lace
- **ASCII depth palette** — 6 shades of blue from deep navy to silver, matched to wave brightness
- **Infinite loop** — a seamless 20-second cycle that plays forever at ~30 fps

---

## 🚀 Quick Start

> Requires **Python 3.10+**

```bash
# 1. Clone the repo
git clone https://github.com/riti2043/night-tide.git
cd night-tide

# 2. (Optional but recommended) Create a virtual environment
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate  # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run
python night_tide.py
```

### Controls

| Key | Action |
|-----|--------|
| `Space` | Pause / Resume |
| `R` | Restart from the beginning |
| `S` | Save a screenshot (PNG) |
| `Esc` | Quit |

---

## 🛠️ How It Works

The whole artwork lives in a **single Python file**. Every cell on screen asks:
> *"What part of the sea am I looking at, and how much light does it catch?"*

| Step | What happens |
|------|-------------|
| **Camera** | A perspective grid maps each screen cell to a point on the water surface |
| **Ocean** | 10 Gerstner swells of varying size, speed, and direction are summed |
| **Light** | Surface normals → sky reflection → Fresnel factor → brightness |
| **Breakers** | Procedural waves roll in, stand up, break, and dissolve into foam |
| **Sand** | Swash runs up the beach, recedes, and leaves a fading foam line |
| **Rendering** | Brightness maps to ASCII density; 6 blues + silver + white |

> See [`HOW_IT_WORKS.txt`](HOW_IT_WORKS.txt) for the full technical breakdown.

---

## 📦 Dependencies

```
numpy>=1.24
pygame-ce>=2.5
```

---

## 🖥️ Compatibility

| Platform | Status |
|----------|--------|
| Windows 11 + Python 3.13 | ✅ Tested |
| Python 3.10 – 3.12 | ✅ Expected to work |
| macOS / Linux | ✅ Expected to work |

---

## 📄 License

Free for personal projects. Please don't sell it or claim it as your own. See [`LICENSE.txt`](LICENSE.txt) for details.

---

*Made by **JIN2** · [@jin_22ee](https://instagram.com/jin_22ee) · 2026*
