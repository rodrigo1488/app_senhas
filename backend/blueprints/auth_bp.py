"""Login/logout do painel administrativo (Supabase)."""
import os

import supabase
from flask import Blueprint, flash, make_response, redirect, render_template, request, session, url_for

auth_bp = Blueprint("auth", __name__)

_supa_client = None


def get_supabase_client():
    global _supa_client
    if _supa_client is None:
        _supa_client = supabase.create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    return _supa_client


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session and request.cookies.get("setor_id"):
        return redirect(url_for("filas.render_senhas"))

    if request.method == "POST":
        email = request.form["email"]
        senha = request.form["senha"]

        response = get_supabase_client().from_("users").select("*").eq("email", email).single().execute()

        if response.data:
            user = response.data
            if user["senha"] == senha:
                session["user_id"] = user["id"]
                session.permanent = True
                resp = make_response(redirect(url_for("setores.selecionar_setor")))
                resp.set_cookie("user_id", str(user["id"]), max_age=60 * 60 * 24 * 365)
                resp.set_cookie("nome_empresa", str(user.get("nome_empresa", "")), max_age=60 * 60 * 24 * 365)
                return resp
            flash("Senha incorreta.", "error")
            return render_template("login.html"), 401
        flash("Usuário não encontrado.", "error")
        return render_template("login.html"), 404

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
