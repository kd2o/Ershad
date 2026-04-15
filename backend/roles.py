ROLE_USER = "user"
ROLE_ADMIN = "admin"
ROLE_MENTOR = "mentor"
ROLE_GUIDANCE_COMMITTEE = "guidance_committee"

DEFAULT_ROLE = ROLE_USER

ROLE_LABELS = {
    ROLE_USER: "طالب",
    ROLE_ADMIN: "Admin",
    ROLE_MENTOR: "المرشد التربوي",
    ROLE_GUIDANCE_COMMITTEE: "اللجنة الإرشادية",
}

VALID_ROLES = tuple(ROLE_LABELS.keys())
STAFF_ROLES = {ROLE_ADMIN, ROLE_MENTOR, ROLE_GUIDANCE_COMMITTEE}

CHAT_SERVICE_OPTIONS = (
    {
        "value": ROLE_MENTOR,
        "label": "المرشد التربوي",
        "description": "للاستفسارات الفردية والدعم الأكاديمي والتربوي المباشر مع المرشد.",
    },
    {
        "value": ROLE_GUIDANCE_COMMITTEE,
        "label": "اللجنة الإرشادية",
        "description": "للحالات التي تحتاج متابعة جماعية أو قرارا مشتركا من اللجنة الإرشادية.",
    },
)

CHAT_SERVICE_LABELS = {
    option["value"]: option["label"] for option in CHAT_SERVICE_OPTIONS
}

CHAT_SERVICE_DESCRIPTIONS = {
    option["value"]: option["description"] for option in CHAT_SERVICE_OPTIONS
}


def normalize_role(role):
    normalized_role = str(role or "").strip().lower()
    return normalized_role if normalized_role in ROLE_LABELS else DEFAULT_ROLE


def get_role_label(role):
    return ROLE_LABELS.get(normalize_role(role), ROLE_LABELS[DEFAULT_ROLE])


def is_staff_role(role):
    return normalize_role(role) in STAFF_ROLES


def can_access_user_management(role):
    return is_staff_role(role)


def can_add_users(role):
    return normalize_role(role) in {ROLE_ADMIN, ROLE_MENTOR}


def can_delete_role(actor_role, target_role):
    normalized_actor_role = normalize_role(actor_role)
    normalized_target_role = normalize_role(target_role)

    if not can_access_user_management(normalized_actor_role):
        return False

    if normalized_actor_role == ROLE_GUIDANCE_COMMITTEE and normalized_target_role == ROLE_ADMIN:
        return False

    return True


def can_manage_schedule(role):
    return is_staff_role(role)


def can_post_news(role):
    return is_staff_role(role)


def normalize_chat_service(service_type):
    normalized_service = str(service_type or "").strip().lower()
    return normalized_service if normalized_service in CHAT_SERVICE_LABELS else ROLE_MENTOR


def is_valid_chat_service(service_type):
    return str(service_type or "").strip().lower() in CHAT_SERVICE_LABELS


def get_chat_service_label(service_type):
    return CHAT_SERVICE_LABELS[normalize_chat_service(service_type)]


def get_chat_service_description(service_type):
    return CHAT_SERVICE_DESCRIPTIONS[normalize_chat_service(service_type)]


def can_handle_chat_service(role, service_type):
    normalized_role = normalize_role(role)
    normalized_service = normalize_chat_service(service_type)
    return normalized_role == ROLE_ADMIN or normalized_role == normalized_service
