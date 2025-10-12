from flask import jsonify
from app.api.routes import app
from ..services import template_service


@app.route("/chatbots/<chatbot_id>/template", methods=["POST"])
def configure_chatbot_template(chatbot_id):
    return jsonify(template_service.configure_template_for_chatbot_service(chatbot_id))


@app.route("/chatbots/<chatbot_id>/template", methods=["PUT"])
def update_chatbot_template(chatbot_id):
    return jsonify(template_service.update_chatbot_template_service(chatbot_id))


@app.route("/chatbots/<chatbot_id>/template", methods=["GET"])
def get_chatbot_template(chatbot_id):
    template = template_service.get_chatbot_template_service(chatbot_id)
    return jsonify({"chatbot_id": chatbot_id, "template": template})


@app.route("/templates", methods=["GET"])
def get_all_templates_global():
    return jsonify(template_service.get_all_templates_service())


@app.route("/templates", methods=["POST"])
def create_template_global():
    template = template_service.create_global_template_service()
    return jsonify({"message": "Template created successfully", "template": template}), 201


@app.route("/templates/<int:template_id>", methods=["GET"])
def get_template_global(template_id):
    return jsonify(template_service.get_template_by_id_service(template_id))


@app.route("/templates/<int:template_id>", methods=["PUT"])
def update_template_global(template_id):
    template = template_service.update_global_template_service(template_id)
    return jsonify({"message": "Template updated successfully", "template": template})


@app.route("/templates/<int:template_id>", methods=["DELETE"])
def delete_template_global(template_id):
    return jsonify(template_service.delete_global_template_service(template_id))


@app.route("/templates/<int:template_id>/preview", methods=["POST"])
def preview_template_global(template_id):
    return jsonify(template_service.preview_template_service(template_id))
