from flask import Flask, redirect, render_template, request, session, url_for

from .config import (
    BASE_URL,
    PORT,
    SESSION_SECRET,
)

from .db import delete_link, get_link, init_db, upsert_link
from .services import (
    AppError,
    assign_rank_roles,
    build_discord_oauth_url,
    exchange_code_for_token,
    extract_riot_from_connections,
    fetch_account,
    fetch_mmr,
    get_default_region,
    get_discord_connections,
    get_discord_user,
    now_iso,
    parse_rank_name,
    random_state,
    remove_rank_roles,
    validate_riot_id,
)

app = Flask(__name__)
app.secret_key = SESSION_SECRET

init_db()


@app.get("/")
def index():
    existing = None
    if session.get("discord_id"):
        existing = get_link(session["discord_id"])
    return render_template("index.html", existing=existing, base_url=BASE_URL)


@app.get("/login")
def login():
    state = random_state()
    session["oauth_state"] = state
    return redirect(build_discord_oauth_url(state))


@app.get("/callback")
def callback():
    if request.args.get("state") != session.get("oauth_state"):
        return render_template("error.html", message="Estado OAuth inválido. Tente novamente.")

    code = request.args.get("code")
    if not code:
        return render_template("error.html", message="Código OAuth ausente.")

    try:
        token_data = exchange_code_for_token(code)
        access_token = token_data["access_token"]
        user = get_discord_user(access_token)
        connections = get_discord_connections(access_token)
        riot = extract_riot_from_connections(connections)

        session["discord_access_token"] = access_token
        session["discord_id"] = user["id"]
        session["discord_username"] = user["username"]
        session["discord_avatar"] = user.get("avatar")
        session["riot_detected_name"] = riot[0] if riot else ""
        session["riot_detected_tag"] = riot[1] if riot else ""

        if riot:
            return redirect(url_for("link_account_auto"))
        return redirect(url_for("manual_riot"))
    except AppError as exc:
        return render_template("error.html", message=str(exc))


@app.get("/link/auto")
def link_account_auto():
    discord_id = session.get("discord_id")
    discord_username = session.get("discord_username")
    name = session.get("riot_detected_name")
    tag = session.get("riot_detected_tag")

    if not (discord_id and discord_username and name and tag):
        return redirect(url_for("manual_riot"))

    try:
        region = get_default_region()

        fetch_account(region, name, tag)
        mmr = fetch_mmr(region, name, tag)

        data = mmr.get("data", {})
        current = data.get("current", {}) or data.get("current_data", {})

        tier_name = (
           current.get("tier", {}).get("name")
           or current.get("currenttierpatched")
           or ""
        )

        rank_name = parse_rank_name(current)
        rr = int(current.get("rr") or current.get("ranking_in_tier") or 0)


        assign_rank_roles(discord_id, rank_name)

        upsert_link(
            discord_id=discord_id,
            discord_username=discord_username,
            riot_name=name,
            riot_tag=tag,
            region=region,
            tier_name=tier_name or "Sem elo detectado",
            rank_name=rank_name or "Sem elo",
            rr=rr,
            last_updated=now_iso(),
        )

        link = get_link(discord_id)
        return render_template("success.html", link=link, auto=True)

    except AppError as exc:
        return render_template(
            "manual_riot.html",
            error=str(exc),
            suggested_name=name,
            suggested_tag=tag,
        )


@app.route("/manual", methods=["GET", "POST"])
def manual_riot():
    if request.method == "GET":
        return render_template(
            "manual_riot.html",
            suggested_name=session.get("riot_detected_name", ""),
            suggested_tag=session.get("riot_detected_tag", ""),
            error=None,
        )

    discord_id = session.get("discord_id")
    discord_username = session.get("discord_username")
    if not (discord_id and discord_username):
        return redirect(url_for("index"))

    try:
        name, tag = validate_riot_id(
            request.form.get("riot_name", ""),
            request.form.get("riot_tag", ""),
        )
        region = request.form.get("region", get_default_region())

        fetch_account(region, name, tag)
        mmr = fetch_mmr(region, name, tag)

        data = mmr.get("data", {})
        current = data.get("current", {}) or data.get("current_data", {})

        tier_name = (
            current.get("tier", {}).get("name")
            or current.get("currenttierpatched")
            or ""
        )

        rank_name = parse_rank_name(current)
        rr = int(current.get("rr") or current.get("ranking_in_tier") or 0)

        assign_rank_roles(discord_id, rank_name)

        upsert_link(
            discord_id=discord_id,
            discord_username=discord_username,
            riot_name=name,
            riot_tag=tag,
            region=region,
            tier_name=tier_name or "Sem elo detectado",
            rank_name=rank_name or "Sem elo",
            rr=rr,
            last_updated=now_iso(),
        )

        link = get_link(discord_id)
        return render_template("success.html", link=link, auto=False)

    except AppError as exc:
        return render_template(
            "manual_riot.html",
            error=str(exc),
            suggested_name=request.form.get("riot_name", ""),
            suggested_tag=request.form.get("riot_tag", ""),
        )

@app.post("/reset")
def reset_link():
    discord_id = session.get("discord_id")
    if not discord_id:
        return redirect(url_for("index"))

    try:
        remove_rank_roles(discord_id)
        delete_link(discord_id)
        return render_template("reset_done.html")
    except AppError as exc:
        return render_template("error.html", message=str(exc))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=True)
