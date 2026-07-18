"""Route blueprints registration."""

from flask import Flask


def register_blueprints(app: Flask) -> None:
    from routes.jobs import jobs_bp
    from routes.review import review_bp

    app.register_blueprint(jobs_bp, url_prefix='/api')
    app.register_blueprint(review_bp, url_prefix='/api')
