"""Example restaurant deployment — wire endpoint_url / MCP when customer is ready."""

from library.industries.templates import restaurant_template
from library.config.loader import save_deployment
from pathlib import Path

if __name__ == "__main__":
    dep = restaurant_template("co_demo_bistro", "Harbor Bistro")
    dep.phone_numbers = ["+15555550101"]
    dep.status = "active"
    out = Path(__file__).resolve().parents[1] / "examples" / "harbor_bistro.json"
    save_deployment(dep, out)
    print(f"Wrote {out}")
