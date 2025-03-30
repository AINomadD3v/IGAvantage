CONFIG = {
    # Delay ranges (in seconds)
    "delays": {
        "after_like": (1.8, 2.3),
        "between_scrolls": (2.0, 3.0),
        "before_scroll": (1.5, 2.2),
        "after_post_tap": (1.0, 1.5),
        "after_comment": (1.2, 2.0),
        "comment_scroll": (1.5, 2.5),
        "back_delay": (1.0, 1.0),  # kept as tuple for consistency
    },

    # Session settings
    "session_duration_secs": 120,
    "max_scrolls": 100,
    "percent_reels_to_watch": 0.2,   # 0.0 to 1.0
    "percent_reels_to_like": 0.8,    # 0.0 to 1.0

    # Interaction probabilities
    "like_probability": 0.8,
    "comment_probability": 0.15,

    # Idle behavior
    "idle_after_actions": (3, 6),
    "idle_duration_range": (2, 9),

    # Package name
    "package_name": "com.instagram.androie",
}

