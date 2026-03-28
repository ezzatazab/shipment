frappe.ui.form.on("User", {
    refresh: function (frm) {
        frm.events.check_roles_permissions(frm);
    },

    onload_post_render: function (frm) {
        frm.events.check_roles_permissions(frm);
    },

    check_roles_permissions: function (frm) {
        setTimeout(() => {
            // let can_edit_roles = has_common(frappe.user_roles, roles_for_editing_user());

            // if (can_edit_roles) {
            //     frm.roles_editor.disable = 0;
            //     frm.module_editor.disable = 0;

            //     $(".deselect-all, .select-all").prop("disabled", false);
            // } else {
            //     frm.roles_editor.disable = 1;
            //     $(".deselect-all, .select-all").prop("disabled", true);

            //     // frm.module_editor.disable = 1;
            // }
            
            // frm.module_editor.show();
            // frm.roles_editor.show();

            if (frappe.session.user != "Administrator") {
                frm.set_df_property("roles_html", "hidden", 1);
                frm.set_df_property("modules_html", "hidden", 1);
                frm.set_df_property("module_profile", "read_only", 0);
            }
        }, 500);
    }
});

function roles_for_editing_user() {
    return (
        frappe
            .get_meta("User")
            .permissions.filter((perm) => perm.permlevel >= 2 && perm.write)
            .map((perm) => perm.role) || ["System Manager"]
    );
};