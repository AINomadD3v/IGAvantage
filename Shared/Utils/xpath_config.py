# xpath_config.py


class InstagramXPaths:
    def __init__(self, package_name="com.instagram.androie"):
        self.package_name = package_name

    @property
    def creation_tab(self):
        return f"//android.widget.FrameLayout[@resource-id='{self.package_name}:id/creation_tab']"

    @property
    def recents(self):
        return f"//android.widget.TextView[@resource-id='{self.package_name}:id/gallery_folder_menu_tv']"

    @property
    def next_button(self):
        return f'//android.widget.Button[@content-desc="Next"]'

    @property
    def reel_button(self):
        return f'//android.widget.Button[@content-desc="Reel"]'

    @property
    def see_all_albums(self):
        return f"//android.widget.TextView[@resource-id='{self.package_name}:id/button_see_all']"

    @property
    def next_button_textview(self):
        return f"//android.widget.TextView[@resource-id='{self.package_name}:id/next_button_textview']"

    @property
    def creation_next_button(self):
        return f"//android.widget.TextView[@resource-id='{self.package_name}:id/creation_next_button']"

    @property
    def image_share_button(self):
        return f"//android.widget.Button[@resource-id='{self.package_name}:id/share_footer_button']"

    @property
    def reels_share_button(self):
        return f"//android.widget.Button[@content-desc='Share']"

    @property
    def reel_caption_text_view(self):
        return f"//android.widget.AutoCompleteTextView[@resource-id='{self.package_name}:id/caption_input_text_view']"

    @property
    def caption_text_view(self):
        return f"//android.widget.AutoCompleteTextView[@resource-id='{self.package_name}:id/caption_text_view']"

    @property
    def action_bar_large_title_auto_size(self):
        return f"//android.widget.TextView[@resource-id='{self.package_name}:id/action_bar_large_title_auto_size']"

    @property
    def media_music_button(self):
        return f"//android.widget.ImageView[@resource-id='{self.package_name}:id/media_music_button']"

    @property
    def story_avatar(self):
        return (
            '//android.widget.ImageView[contains(@content-desc, "\'s story at column")]'
        )

    @property
    def tab_bar(self):
        return f'//android.widget.LinearLayout[@resource-id="{self.package_name}:id/tab_bar"]'

    @property
    def create_new_account(self):
        return "//android.view.View[@text='Create new account']"

    @property
    def album_container(self):
        return f"//android.widget.GridView[@resource-id='{self.package_name}:id/album_thumbnail_recycler_view']"

    def album_selector(self, album_name):
        return f'//android.widget.LinearLayout[contains(@content-desc, "{album_name}")]'

    @property
    def image_thumbnails(self):
        return f"//android.view.ViewGroup[contains(@content-desc, 'Photo thumbnail')]"

    @property
    def tos_popup(self):
        return f"//android.view.View[@content-desc='Terms and Privacy Policy']"

    @property
    def add_sound(self):
        return f'//android.widget.Button[@content-desc="Add audio"]'

    @property
    def tracks_list(self):
        return f"//androidx.recyclerview.widget.RecyclerView[@resource-id='{self.package_name}:id/content_list']"

    @property
    def track_container(self):
        return f"//android.view.ViewGroup[@resource-id='{self.package_name}:id/track_container']"

    @property
    def click_done(self):
        return f"//android.widget.Button[@content-desc='Done']"

    @property
    def signup_with_email(self):
        return f"//android.widget.Button[@content-desc='Sign up with email']"

    @property
    def email_input(self):
        return f"//android.widget.EditText"

    @property
    def confirmation_code_input(self):
        return f"//android.widget.EditText"

    @property
    def click_select_song(self):
        """The click_select_song property."""
        return f"//android.widget.FrameLayout[@resource-id='{self.package_name}:id/select_button_tap_target']"

    @property
    def new_password_entry_field(self):
        return f"//android.widget.FrameLayout[@resource-id='{self.package_name}:id/layout_container_main']/android.widget.FrameLayout/android.widget.FrameLayout[2]/android.widget.FrameLayout[1]/android.view.ViewGroup/android.view.ViewGroup/android.view.ViewGroup/android.view.ViewGroup/android.view.ViewGroup/android.view.ViewGroup[2]/android.view.ViewGroup/android.widget.EditText"

    # --- XPaths from instagram_actions.py ---

    @property
    def create_post_general_button(self):
        # Was: "//*[contains(@content-desc, 'Create')]"
        # In: InstagramInteractions.new_post
        return "//*[contains(@content-desc, 'Create')]"

    @property
    def gallery_grid_container(self):
        # Was: grid_xpath = "//android.widget.GridView[contains(@resource-id, 'gallery_recycler_view')]/android.view.ViewGroup"
        # In: InstagramInteractions.select_first_video
        return "//android.widget.GridView[contains(@resource-id, 'gallery_recycler_view')]/android.view.ViewGroup"

    @property
    def gallery_loaded_video_thumbnail_sub_xpath(self):
        # Was: loaded_thumb_xpath = ".//android.view.View[contains(@resource-id, 'gallery_grid_item_thumbnail') and starts-with(@content-desc, 'Video thumbnail')]"
        # In: InstagramInteractions.select_first_video
        # Usage: parent_element.xpath(self.gallery_loaded_video_thumbnail_sub_xpath)
        return ".//android.view.View[contains(@resource-id, 'gallery_grid_item_thumbnail') and starts-with(@content-desc, 'Video thumbnail')]"

    @property
    def reel_viewer_insights_pill(self):
        # Was: insights_xpath = "//android.view.ViewGroup[contains(@resource-id, 'clips_viewer_insights_pill')]"
        # In: InstagramInteractions.wait_for_posted_caption
        return "//android.view.ViewGroup[contains(@resource-id, 'clips_viewer_insights_pill')]"

    # For SoundAdder.add_music_to_reel and post_reel.py for device.xpath("Add audio")
    # Note: Your existing 'add_sound' property is '//android.widget.Button[@content-desc="Add audio"]'
    # This new one is for the more flexible text or content-desc search.
    @property
    def add_audio_text_or_desc_general(self):
        # Replaces device.xpath("Add audio")
        return (
            "//*[contains(@text, 'Add audio') or contains(@content-desc, 'Add audio')]"
        )

    @property
    def trending_text_or_desc_general(self):
        # Replaces device.xpath("Trending") in SoundAdder.add_music_to_reel
        return "//*[contains(@text, 'Trending') or contains(@content-desc, 'Trending')]"

    @property
    def audio_bottom_sheet_drag_handle_rids(self):
        # Was: possible_ids = ["bottom_sheet_drag_handle_prism", "bottom_sheet_drag_handle"]
        # In: SoundAdder.add_music_to_reel (used to construct XPaths like //*[contains(@resource-id, '{rid}')])
        # This property returns the list of ID parts directly.
        return ["bottom_sheet_drag_handle_prism", "bottom_sheet_drag_handle"]

    @property
    def audio_tracks_list_general(self):
        # Was: "//*[contains(@resource-id, 'content_list') or contains(@resource-id, 'preview_items')]"
        # In: SoundAdder.add_music_to_reel
        # This is an alternative/more general version than your existing 'tracks_list'.
        return "//*[contains(@resource-id, 'content_list') or contains(@resource-id, 'preview_items')]"

    @property
    def audio_track_container_general(self):
        # Was: "//*[contains(@resource-id, 'track_container')]"
        # In: SoundAdder.add_music_to_reel
        # This is an alternative/more general version than your existing 'track_container'.
        return "//*[contains(@resource-id, 'track_container')]"

    @property
    def audio_select_song_button_general(self):
        # Was: "//*[contains(@resource-id, 'select_button_tap_target')]"
        # In: SoundAdder.add_music_to_reel
        # This is an alternative/more general version than your existing 'click_select_song'.
        return "//*[contains(@resource-id, 'select_button_tap_target')]"

    @property
    def audio_scrubber_view(self):
        # Was: scrubber_xpath = "//*[contains(@resource-id, 'scrubber_recycler_view')]"
        # In: SoundAdder.add_music_to_reel and SoundAdder.scrub_music
        return "//*[contains(@resource-id, 'scrubber_recycler_view')]"

    # --- XPaths from post_reel.py ---

    @property
    def home_feed_ready_identifier(self):
        # Was: expected_xpath = '//android.widget.Button[@content-desc="Instagram Home Feed"]'
        # In: post_reel (for wait_for_app_ready)
        return '//android.widget.Button[@content-desc="Instagram Home Feed"]'

    @property
    def reel_creation_tab_general(self):
        # Replaces device.xpath("REEL") in post_reel.py
        # Note: Your existing 'reel_button' is '//android.widget.Button[@content-desc="Reel"]'
        return "//*[contains(@text, 'REEL') or contains(@content-desc, 'REEL')]"

    @property
    def new_reel_screen_identifier_general(self):
        return "//*[contains(@text, 'New reel') or contains(@content-desc, 'New reel')]"

    @property
    def final_share_or_next_button(self):
        # Was: xpath = "//*[contains(@text, 'Next') or contains(@content-desc, 'Next') or contains(@content-desc, 'Share')]"
        # In: post_reel (for final sharing click)
        # Note: Your 'next_button' and 'reels_share_button' are more specific. This is for the combined case.
        return "//*[contains(@text, 'Next') or contains(@content-desc, 'Next') or contains(@content-desc, 'Share')]"

    @property
    def back_button(self):
        return "//*[@content-desc='Back']"

    @property
    def search_layout_container_frame(self):
        """General FrameLayout often containing search results/posts."""
        # From extract_search_page_reels
        return "//android.widget.FrameLayout"

    @property
    def search_layout_container_rid_pattern(self):
        """Regex pattern for resource-id of layout containers on search/explore. Use with caution."""
        # From extract_search_page_reels - This was used with device.xpath(pattern) directly.
        # It's better to find a more specific, non-regex selector if possible.
        # Keeping it here for reference, but using it might require direct device.xpath().
        return "^.*layout_container$"

    @property
    def search_image_post_button(self):
        """Relative XPath for buttons within a search result container (used to detect image posts)."""
        # From extract_search_page_reels - Note the leading '.' for relative search
        return ".//android.widget.Button"

    @property
    def search_reel_imageview(self):
        """Relative XPath for ImageViews within a search result container (used to find reels)."""
        # From extract_search_page_reels - Note the leading '.'
        return ".//android.widget.ImageView"

    @property
    def search_reel_imageview_template(self):
        """
        Template for finding a specific reel ImageView on the search page using its content description.
        Use as: self.xpath_config.search_reel_imageview_template.format(reel_description)
        """
        # From process_reel (used to tap the specific reel)
        return '//android.widget.ImageView[@content-desc="{}"]'

    @property
    def reel_profile_picture_desc_contains(self):
        """ImageView containing the profile picture and username in the reel view."""
        # From process_reel
        return (
            '//android.widget.ImageView[contains(@content-desc, "Profile picture of")]'
        )

    @property
    def reel_caption_container(self):
        """ViewGroup containing the caption text in the reel view."""
        # From process_reel - Uses package_name
        return f'//android.view.ViewGroup[@resource-id="{self.package_name}:id/clips_caption_component"]//android.view.ViewGroup[contains(@content-desc, "")]'

    @property
    def reel_likes_button_desc(self):
        """ViewGroup associated with the likes count/button in the reel view."""
        # From process_reel
        return '//android.view.ViewGroup[contains(@content-desc, "View likes")]'

    @property
    def reel_reshare_button_desc(self):
        """ViewGroup associated with the reshare count/button in the reel view."""
        # From process_reel
        return '//android.view.ViewGroup[contains(@content-desc, "Reshare number")]'

    @property
    def reel_audio_link_desc_contains(self):
        """ViewGroup containing the audio link/name in the reel view."""
        # From process_reel
        return '//android.view.ViewGroup[contains(@content-desc, "Original audio")]'

    @property
    def reel_follow_button_text(self):
        """The 'Follow' button sometimes visible in the reel view."""
        # From process_reel
        return '//android.widget.Button[@text="Follow"]'

    @property
    def reel_like_or_unlike_button_desc(self):
        """Selector matching either the 'Like' or 'Unlike' button description in the reel view."""
        # Used for verifying exit from reel view in process_reel/navigate_back_from_subscreen
        # Assumes like_button_desc and unlike_button_desc are also defined for specific actions.
        return '//*[@content-desc="Like" or @content-desc="Unlike"]'

    # Note: explore_search_bar_rid and explore_tab_desc were likely defined previously
    # when integrating navigate_to_explore. Ensure they exist.
    # @property
    # def explore_search_bar_rid(self):
    #     """Resource ID pattern for the search bar on the Explore page."""
    #     # From perform_keyword_search
    #     return "//*[contains(@resource-id, 'action_bar_search_edit_text')]"
    #
    # @property
    # def explore_tab_desc(self):
    #     """Content description for the Search/Explore tab."""
    #     # From run_warmup_session (used in open_app readiness check)
    #     return '//android.widget.FrameLayout[@content-desc="Search and explore"]'

    @property
    def search_posts_section_title(self):
        """The 'Posts' title text view appearing in search results."""
        # From perform_keyword_search - Uses package_name
        return f'//*[@resource-id="{self.package_name}:id/title_text_view" and @text="Posts"]'

    @property
    def search_results_recycler_view(self):
        """The RecyclerView likely containing search results (posts/reels)."""
        # From perform_keyword_search
        return "//*[contains(@resource-id, 'recycler_view')]"


# TODO Implement these xpath correcty

# def _is_explore_page(self):
#     return self.d.xpath('//android.widget.TextView[@text="Explore"]').exists

# def _is_reels_page(self):
#     return self.d.xpath('//android.widget.TextView[@text="Reels"]').exists
#
# def _is_home_page(self):
#     return self.d.xpath('//android.widget.TextView[@text="Home"]').exists
#
# def _is_profile_page(self):
#     return self.d.xpath('//android.widget.TextView[@text="Edit profile"]').exists
#
# def _is_notifications_page(self):
#     return self.d.xpath('%All caught up%').exists

# def attempt_like(device, ui):
#     try:
#         el = device.xpath('//*[@content-desc="Like"]').get(timeout=1.5)
#         bounds = el.attrib.get("bounds", "")
#         ui._tap_random_in_bounds(bounds, label="Like Button")
#         time.sleep(1.0)
#         el = device.xpath('//*[@content-desc="Like"]').get(timeout=1.5)
#         return el.attrib.get("selected") == "true"
#     except Exception as e:
#         logger.warning(f"⚠️ Failed to like: {e}")
#         return False
#
#
# def attempt_comment(device, ui):
#     logger.info("💬 Attempting to comment mid-watch...")
#     try:
#         if ui.tap_random_within_element(
#             '//*[contains(@content-desc, "Comment")]', label="Comment Button"
#         ):
#             time.sleep(1.5)
#             device.swipe(540, 1600, 540, 1000, 0.2)
#             time.sleep(1.5)
#             device.press("back")
#             logger.info("💬 Comment interaction complete")
#             return True
#     except Exception as e:
#         logger.warning(f"⚠️ Failed to perform comment interaction: {e}")
#     return False
#
#
# def exit_reel_view(device):
#     try:
#         back_btn = device.xpath('//*[@content-desc="Back"]')
#         if back_btn.exists:
#             back_btn.get().click()
#             logger.info("🖐 Back button clicked directly")
#         time.sleep(1.5)
#     except Exception as e:
#         logger.warning(f"Failed to click Back button: {e}")
#
#     for _ in range(10):
#         if not device.xpath('//*[@content-desc="Like"]').exists:
#             logger.info("✅ Exited reel view")
#             return
#         time.sleep(0.5)
#     logger.warning("⚠️ Still in reel UI after back")
#
#
# def navigate_to_explore(device, ui):
#     explore_xpath = '//android.widget.FrameLayout[@content-desc="Search and explore"]'
#     search_ready_xpath = "//*[contains(@resource-id, 'action_bar_search_edit_text')]"
#
#     logger.info("📍 Navigating to Explore page...")
#     success = ui.tap_random_within_element(explore_xpath, label="Explore Tab")
#     if not success:
#         logger.warning("❌ Could not find Explore tab.")
#         time.sleep(2)
#         return False
#
#     try:
#         device.xpath(search_ready_xpath).wait(timeout=10.0)
#         logger.info("✅ Explore page loaded.")
#         return True
#     except Exception:
#         logger.warning("❌ Search bar not found after tapping Explore.")
#         return False
#
