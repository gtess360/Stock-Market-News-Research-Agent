"""Administrator console for reviewing token requests, issuing tokens, and viewing audit logs."""
import streamlit as st
from src.services.audit_service import get_recent_audit_logs
from src.services.entitlement_service import (
    admin_issue_token,
    admin_list_token_requests,
    admin_revoke_token,
)


def render_admin_console(admin_user) -> None:
    """Render the administrator control panel."""
    st.subheader("🛡️ Administrator Control Console")
    st.caption(f"Authenticated Administrator: {admin_user.auth_provider_subject}")

    tab_requests, tab_issue, tab_audit = st.tabs([
        "📥 Token Requests",
        "🔑 Issue / Revoke Tokens",
        "📜 Security Audit Trail",
    ])

    with tab_requests:
        st.markdown("#### Pending Token Requests")
        requests = admin_list_token_requests(admin_user.id, status_filter="pending")
        if not requests:
            st.info("No pending token requests at this time.")
        else:
            for req in requests:
                with st.container(border=True):
                    col1, col2, col3 = st.columns([2, 3, 2])
                    with col1:
                        st.markdown(f"**Request ID:** `{req.id[:8]}`")
                        st.caption(f"User ID: `{req.user_id[:8]}...`")
                        st.caption(f"Requested: {req.requested_at[:19]}")
                    with col2:
                        st.markdown(f"**Justification:** {req.reason or 'None provided.'}")
                    with col3:
                        if st.button("Approve & Issue Token", key=f"appr_{req.id}", width="stretch"):
                            try:
                                _, raw_tok = admin_issue_token(
                                    admin_user_id=admin_user.id,
                                    recipient_user_id=req.user_id,
                                    expires_in_days=30,
                                )
                                st.success(f"Token Issued! Plaintext: `{raw_tok}`")
                                st.warning("Copy token now; it will never be displayed again.")
                            except Exception as err:
                                st.error(f"Error: {err}")

    with tab_issue:
        col_iss, col_rev = st.columns(2)
        with col_iss:
            st.markdown("#### Manually Issue Access Token")
            with st.form("manual_issue_form"):
                recip_id = st.text_input("Recipient User ID (Optional)")
                exp_days = st.number_input("Expires in (Days)", min_value=1, max_value=365, value=30)
                submit_iss = st.form_submit_button("Generate Unlimited Token", width="stretch")
                if submit_iss:
                    try:
                        token_obj, plaintext = admin_issue_token(
                            admin_user_id=admin_user.id,
                            recipient_user_id=recip_id.strip() or None,
                            expires_in_days=int(exp_days),
                        )
                        st.success(f"Generated Token: `{plaintext}`")
                        st.caption(f"Token ID: `{token_obj.id}` | Prefix: `{token_obj.token_prefix}`")
                        st.warning("Displaying plaintext exactly once. Save it securely.")
                    except Exception as ex:
                        st.error(f"Error: {ex}")

        with col_rev:
            st.markdown("#### Revoke Access Token")
            with st.form("manual_revoke_form"):
                tok_id_rev = st.text_input("Access Token ID to Revoke")
                submit_rev = st.form_submit_button("Revoke Token", width="stretch")
                if submit_rev:
                    if not tok_id_rev:
                        st.error("Please enter a valid Token ID.")
                    else:
                        ok = admin_revoke_token(admin_user.id, tok_id_rev.strip())
                        if ok:
                            st.success(f"Token `{tok_id_rev[:8]}...` revoked successfully.")
                        else:
                            st.error("Token not found or already revoked.")

    with tab_audit:
        st.markdown("#### Recent Security & Operational Audit Events")
        logs = get_recent_audit_logs(limit=20)
        if not logs:
            st.info("No audit logs recorded yet.")
        else:
            table_data = [
                {
                    "Timestamp": l["created_at"][:19],
                    "Action": l["action"],
                    "Actor": f"{l['actor_user_id'][:8]}..." if l["actor_user_id"] else "SYSTEM",
                    "Subject ID": f"{l['subject_id'][:8]}..." if l["subject_id"] else "-",
                    "Metadata": str(l["metadata"])[:60],
                }
                for l in logs
            ]
            st.dataframe(table_data, width="stretch", hide_index=True)

