def _copy_card(name, code, expires_text):
    import html

    safe_name = html.escape(str(name))
    safe_code = html.escape(str(code))
    safe_expiry = html.escape(str(expires_text))
    payload = f"Name: {name}\nCode: {code}"
    safe_payload = (
        payload.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")
    )
    import streamlit.components.v1 as components

    components.html(
        f"""
        <div style="font-family:Arial,sans-serif;background:#0f172a;color:white;border:1px solid #22d3ee;border-radius:14px;padding:14px;margin:4px 0 10px">
          <div style="font-weight:800;margin-bottom:7px">Name: {safe_name}</div>
          <div style="font-weight:800;margin-bottom:7px">Code: {safe_code}</div>
          <div style="opacity:.8;margin-bottom:10px">Expires: {safe_expiry}</div>
          <button onclick="navigator.clipboard.writeText(`{safe_payload}`).then(()=>this.innerText='✅ COPIED')"
            style="width:100%;padding:11px;border:0;border-radius:9px;background:linear-gradient(90deg,#0284c7,#22d3ee);color:white;font-weight:900;cursor:pointer;">
            📋 Copy Credentials
          </button>
        </div>
        """,
        height=140,
    )


def admin_gate_modal():
    """Hidden Owner Admin Portal for Managing Customer Licenses."""
    if not st.session_state.get("admin_gate_visible", False):
        return

    st.markdown("---")
    st.subheader("👑 Owner License Portal")

    if not st.session_state.get("admin_authenticated", False):
        with st.form("admin_login_form"):
            user = st.text_input("Admin Username")
            pwd = st.text_input("Admin Password", type="password")
            if st.form_submit_button("Sign In as Admin"):
                if user == get_admin_username() and pwd == get_admin_password():
                    st.session_state.admin_authenticated = True
                    st.success("Admin access granted.")
                    st.rerun()
                else:
                    st.error("Invalid owner credentials.")
        if st.button("Close Admin Menu"):
            st.session_state.admin_gate_visible = False
            st.rerun()
        return

    # Authenticated Admin Dashboard
    col_a, col_b = st.columns([3, 1])
    with col_a:
        st.write("Logged in as **Owner / Admin**")
    with col_b:
        if st.button("Logout Admin"):
            st.session_state.admin_authenticated = False
            st.session_state.admin_gate_visible = False
            st.rerun()

    tab1, tab2 = st.tabs(["➕ Create License", "📋 Manage Licenses"])

    with tab1:
        with st.form("create_license_form"):
            c_name = st.text_input("Customer Name")
            c_code = st.text_input(
                "Access Code (e.g. KHBR-2026-001)",
                placeholder="KHBR-XXXX-XXXX",
            )
            duration = st.selectbox(
                "Duration",
                [7, 30, 90, 180, 365],
                format_func=lambda x: {
                    7: "7 Days",
                    30: "1 Month",
                    90: "3 Months",
                    180: "6 Months",
                    365: "1 Year",
                }[x],
            )
            if st.form_submit_button("Generate Customer License"):
                try:
                    code, expires, _ = add_license(c_name, c_code, duration)
                    st.success(
                        f"License created for {c_name}! Expiration: {expires.strftime('%d/%m/%Y')}"
                    )
                    _copy_card(c_name, code, expires.strftime("%d/%m/%Y %H:%M"))
                except Exception as exc:
                    st.error(str(exc))

    with tab2:
        search = st.text_input("Search Customer / Code", "")
        rows = license_rows(search)
        for r in rows:
            with st.expander(
                f"👤 {r['customer_name']} | Code: {r['access_code_display']} | Active: {'✅' if r['is_active'] else '❌'}"
            ):
                st.write(f"**Expires:** {r['expires_at']}")
                st.write(f"**Logins:** {r['login_count']}")

                c1, c2, c3 = st.columns(3)
                with c1:
                    if st.button(
                        (
                            "Deactivate"
                            if r["is_active"]
                            else "Reactivate"
                        ),
                        key=f"toggle_{r['id']}",
                    ):
                        update_license_status(
                            r["id"], not bool(r["is_active"])
                        )
                        st.rerun()
                with c2:
                    if st.button("Renew +1 Month", key=f"renew_{r['id']}"):
                        renew_license(r["id"], 30)
                        st.success("Extended by 30 days!")
                        st.rerun()
                with c3:
                    if st.button("Delete License", key=f"del_{r['id']}"):
                        delete_license(r["id"])
                        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# MAIN APPLICATION ROUTING
# ─────────────────────────────────────────────────────────────────────────────
def main():
    initialize_license_database()

    # Secret triple-click trigger for owner access
    hidden_owner_trigger()
    admin_gate_modal()

    # Check session/saved login
    if not st.session_state.get("customer_authenticated", False):
        saved_name, saved_code = _saved_login_get()
        if saved_code:
            ok, _, row, token = validate_customer_login(
                saved_name, saved_code, acquire_session=False
            )
            if ok:
                st.session_state.customer_authenticated = True
                st.session_state.customer_name = row["customer_name"]
                st.session_state.customer_code = row["access_code_display"]
                st.session_state.customer_session_token = token

    if not st.session_state.get("customer_authenticated", False):
        public_login_screen()
        return

    # Top Navigation / Hero
    st.markdown(
        f'<div class="hero"><h1>AI KHEMRA BRO v{APP_VERSION}</h1><p>WELCOME {st.session_state.get("customer_name", "").upper()}</p></div>',
        unsafe_allow_html=True,
    )

    # Main Application Interface Tabs
    tab_srt, tab_edit, tab_audio, tab_settings = st.tabs(
        [
            "🎬 1. Generate Khmer SRT",
            "✏️ 2. Edit SRT",
            "🔊 3. Generate Audio",
            "⚙️ Settings",
        ]
    )

    with tab_settings:
        st.subheader("⚙️ Customer API Key Settings")
        saved_keys = load_private_api_keys()
        api_key_input = st.text_area(
            "Gemini API Keys (One per line for key rotation):",
            value=saved_keys,
            key="api_keys_manager",
            on_change=api_keys_changed,
            height=120,
        )
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            if st.button("💾 Save Key"):
                save_private_api_keys(api_key_input)
                st.success("API Key saved securely.")
        with col_s2:
            if st.button("🗑️ Delete Saved Key"):
                delete_private_api_keys()
                st.session_state.api_keys_manager = ""
                st.warning("API Key deleted.")

        st.markdown("---")
        if st.button("🚪 Sign Out"):
            release_customer_session(
                st.session_state.get("customer_code", ""),
                st.session_state.get("customer_session_token", ""),
            )
            _saved_login_delete()
            _session_cookie_delete()
            st.session_state.customer_authenticated = False
            st.rerun()

    with tab_srt:
        st.subheader(" Upload Video & Translate")
        uploaded_video = st.file_uploader(
            "Upload Movie/Drama Video (MP4, MKV, MOV):",
            type=["mp4", "mkv", "mov", "webm"],
        )

        model_choice = st.selectbox(
            "Gemini Translation Model:",
            [
                "gemini-2.5-flash-lite",
                "gemini-2.5-flash",
                "gemini-flash-latest",
            ],
        )

        if uploaded_video and st.button(
            "🚀 Generate Khmer SRT", key="generate_srt"
        ):
            api_keys = load_private_api_keys().splitlines()
            if not api_keys or not any(k.strip() for k in api_keys):
                st.error("Please enter a valid Gemini API key in Settings ⚙️.")
            else:
                with st.spinner("Processing video and translating into Khmer..."):
                    try:
                        v_path = save_upload(uploaded_video)
                        srt_res = video_to_srt(v_path, api_keys, model_choice)
                        st.session_state.srt_text = srt_res
                        st.success("Khmer SRT Generated Successfully!")
                    except Exception as exc:
                        st.error(f"Error: {exc}")

    with tab_edit:
        st.subheader("✏️ Review & Edit Subtitles")
        srt_val = st.text_area(
            "Khmer Subtitle Editor (SRT Format):",
            value=st.session_state.get("srt_text", ""),
            height=320,
        )
        st.session_state.srt_text = srt_val

        if st.session_state.get("source_srt_text"):
            st.download_button(
                "📥 Download Source SRT",
                data=st.session_state.source_srt_text,
                file_name="source_subtitles.srt",
                mime="text/plain",
            )

    with tab_audio:
        st.subheader("🔊 Dubbing Audio Generation")
        if not st.session_state.get("srt_text", "").strip():
            st.info("Please generate or enter Khmer SRT content first.")
        else:
            if st.button("🎙️ Generate Dubbed Audio (MP3)"):
                try:
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    def update_p(pct, msg):
                        progress_bar.progress(pct)
                        status_text.text(msg)

                    mp3_data = create_mp3(
                        st.session_state.srt_text, progress_callback=update_p
                    )
                    st.session_state.audio_bytes = mp3_data
                    st.success("MP3 Generated Successfully!")
                except Exception as exc:
                    st.error(f"Failed to generate audio: {exc}")

            if st.session_state.get("audio_bytes"):
                st.audio(st.session_state.audio_bytes, format="audio/mp3")
                st.download_button(
                    "📥 Download Dubbed MP3",
                    data=st.session_state.audio_bytes,
                    file_name=f"{st.session_state.get('mp3_download_name', 'khmer_dubbed')}.mp3",
                    mime="audio/mp3",
                )


if __name__ == "__main__":
    main()
