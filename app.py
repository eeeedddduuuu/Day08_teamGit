"""
Flask 入口 — 智能数字媒体内容审核系统
方向 A：智能数字媒体内容审核
"""
from flask import Flask

app = Flask(__name__)


@app.route("/api/health")
def health():
    """健康检查"""
    import os
    model_path = os.path.join(os.path.dirname(__file__), "models", "yolo11n.pt")
    return {
        "status": "ok",
        "model_ready": os.path.exists(model_path),
        "direction": "A"
    }


if __name__ == "__main__":
    app.run(debug=True, port=5000)
