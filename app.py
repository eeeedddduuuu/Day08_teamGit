"""
Team Content Review — Flask Application Entry
方向 A：智能数字媒体内容审核系统
"""
import os
import sys
from flask import Flask, jsonify, render_template, send_from_directory, request, Response

# Ensure project root on path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from routes import register_blueprints


def create_app() -> Flask:
    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 MB
    app.config['PROJECT_ROOT'] = PROJECT_ROOT
    app.config['OUTPUTS_DIR'] = os.path.join(PROJECT_ROOT, 'outputs')
    app.config['MODEL_PATH'] = os.path.join(PROJECT_ROOT, 'models', 'yolo11n.pt')

    # Ensure output directory exists
    os.makedirs(app.config['OUTPUTS_DIR'], exist_ok=True)

    # Register route blueprints
    register_blueprints(app)

    return app


app = create_app()


@app.route('/')
def index():
    """Render the main workbench page."""
    return render_template('index.html')


@app.route('/outputs/<job_id>/<path:filename>')
def serve_output(job_id, filename):
    """Serve files from outputs directory — supports video Range requests."""
    import mimetypes
    outputs_dir = app.config['OUTPUTS_DIR']
    filepath = os.path.join(outputs_dir, job_id, filename)
    # 安全检查
    real = os.path.realpath(filepath)
    if not real.startswith(os.path.realpath(outputs_dir)):
        return jsonify({"ok": False, "error": "路径非法"}), 403
    if not os.path.isfile(real):
        return jsonify({"ok": False, "error": "文件不存在"}), 404

    file_size = os.path.getsize(real)
    range_header = request.headers.get('Range', None)
    mimetype, _ = mimetypes.guess_type(real)
    if mimetype is None:
        mimetype = 'application/octet-stream'

    if range_header:
        # 支持 Range 请求（视频播放必需）
        byte_range = range_header.replace('bytes=', '').split('-')
        start = int(byte_range[0]) if byte_range[0] else 0
        end = int(byte_range[1]) if len(byte_range) > 1 and byte_range[1] else file_size - 1
        if start >= file_size:
            return Response(status=416)
        length = end - start + 1
        with open(real, 'rb') as f:
            f.seek(start)
            data = f.read(length)
        resp = Response(data, 206, mimetype=mimetype, direct_passthrough=True)
        resp.headers.add('Content-Range', f'bytes {start}-{end}/{file_size}')
        resp.headers.add('Accept-Ranges', 'bytes')
        resp.headers.add('Content-Length', str(length))
        return resp
    else:
        return send_from_directory(os.path.join(outputs_dir, job_id), filename)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Team Content Review Server')
    parser.add_argument('--host', default='127.0.0.1', help='Bind host')
    parser.add_argument('--port', type=int, default=7880, help='Bind port')
    parser.add_argument('--debug', action='store_true', help='Debug mode')
    args = parser.parse_args()

    app.run(host=args.host, port=args.port, debug=args.debug)
