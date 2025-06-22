# xpath_config.py


# Shared/Utils/xpath_config.py


class InstagramXPaths:
    def __init__(
        self, package_name="com.instagram.androie"
    ):  # Corrected your default here if it was a typo
        self.package_name = package_name

    # --- START: Existing XPaths from your provided class ---
    @property
    def creation_tab(self):
        return f"//android.widget.FrameLayout[@resource-id='{self.package_name}:id/creation_tab']"

    @property
    def recents(self):
        return f"//android.widget.TextView[@resource-id='{self.package_name}:id/gallery_folder_menu_tv']"

    @property
    def next_button(self):  # General Next button
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
    def reels_share_button(self):  # Final Share button for Reels
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
    def add_sound(self):  # This is likely the "Add audio" button on the main edit page
        return f'//android.widget.Button[@content-desc="Add audio"]'

    @property
    def tracks_list(self):
        return f"//androidx.recyclerview.widget.RecyclerView[@resource-id='{self.package_name}:id/content_list']"

    @property
    def track_container(self):
        return f"//android.view.ViewGroup[@resource-id='{self.package_name}:id/track_container']"

    @property
    def click_done(self):  # General Done button, context is important
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
        return f"//android.widget.FrameLayout[@resource-id='{self.package_name}:id/select_button_tap_target']"

    @property
    def new_password_entry_field(self):
        return f"//android.widget.FrameLayout[@resource-id='{self.package_name}:id/layout_container_main']/android.widget.FrameLayout/android.widget.FrameLayout[2]/android.widget.FrameLayout[1]/android.view.ViewGroup/android.view.ViewGroup/android.view.ViewGroup/android.view.ViewGroup/android.view.ViewGroup/android.view.ViewGroup[2]/android.view.ViewGroup/android.widget.EditText"

    @property
    def post_login_save_button_text_en(self):
        return '//android.widget.Button[contains(@text, "Save") or contains(@content-desc, "Save")]'

    @property
    def post_login_save_button_text_pl(self):
        return '//android.widget.Button[contains(@text, "Zapisz") or contains(@content-desc, "Zapisz")]'

    @property
    def post_login_not_now_button_text_en(self):
        return '//android.widget.Button[contains(@text, "Not now") or contains(@content-desc, "Not now")]'

    @property
    def post_login_not_now_button_text_pl(self):
        return '//android.widget.Button[contains(@text, "Nie teraz") or contains(@content-desc, "Nie teraz")]'

    @property
    def setup_on_new_device_prompt_smart(self):
        return "%Set up on new device%"

    @property
    def skip_button_smart(self):
        return "^Skip"

    @property
    def login_username_label_smart(self):
        return "^Username, email or mobile number"

    @property
    def login_password_label_smart(self):
        return "^Password"

    @property
    def login_edittext_field_generic(self):
        return "//android.widget.EditText"

    @property
    def login_show_password_button(self):
        return '//android.widget.Button[@content-desc="Show password"]'

    @property
    def login_button(self):
        return '//android.widget.Button[@content-desc="Log in"]'

    @property
    def two_fa_check_email_text_view(self):
        return '//android.widget.TextView[contains(@text, "check your email")]'

    @property
    def two_fa_prompt_view_desc(self):
        return '//android.view.View[@content-desc="Check your email"]'

    @property
    def two_fa_code_input_field(self):
        return "//android.widget.EditText"

    @property
    def save_login_info_prompt_smart(self):
        return "^Save your login info%"

    @property
    def save_login_info_save_button(self):
        return '//android.widget.Button[@content-desc="Save"]'

    @property
    def turn_on_notifications_prompt_smart(self):
        return "%Turn on notifications%"

    @property
    def home_your_story_text(self):
        return '//android.widget.TextView[@text="Your story"]'

    def home_user_story_button(self, username: str) -> str:
        return (
            f'//android.widget.Button[contains(@content-desc, "{username}\\\'s story")]'
        )

    def home_user_story_image(self, username: str) -> str:
        return f'//android.widget.ImageView[contains(@content-desc, "{username}\\\'s story")]'

    @property
    def login_incorrect_password_text_view(self):
        return '//android.widget.TextView[@text="Incorrect Password"]'

    @property
    def login_incorrect_password_ok_button(self):
        return '//android.widget.Button[@text="OK"]'

    @property
    def account_suspended_text_smart(self):
        return "%We suspended your account%"

    @property
    def create_post_general_button(self):
        return "//*[contains(@content-desc, 'Create')]"

    @property
    def gallery_grid_container(self):
        return "//android.widget.GridView[contains(@resource-id, 'gallery_recycler_view')]/android.view.ViewGroup"

    @property
    def gallery_loaded_video_thumbnail_sub_xpath(self):
        return ".//android.view.View[contains(@resource-id, 'gallery_grid_item_thumbnail') and starts-with(@content-desc, 'Video thumbnail')]"

    @property
    def reel_viewer_insights_pill(self):
        return f"//android.view.ViewGroup[contains(@resource-id, '{self.package_name}:id/clips_viewer_insights_pill')]"  # Added package name

    @property
    def add_audio_text_or_desc_general(self):
        return (
            "//*[contains(@text, 'Add audio') or contains(@content-desc, 'Add audio')]"
        )

    @property
    def trending_text_or_desc_general(self):
        return "//*[contains(@text, 'Trending') or contains(@content-desc, 'Trending')]"

    @property
    def audio_bottom_sheet_drag_handle_rids(self):
        return ["bottom_sheet_drag_handle_prism", "bottom_sheet_drag_handle"]

    @property
    def audio_tracks_list_general(self):
        return "//*[contains(@resource-id, 'content_list') or contains(@resource-id, 'preview_items')]"

    @property
    def audio_track_container_general(self):
        return "//*[contains(@resource-id, 'track_container')]"

    @property
    def audio_select_song_button_general(self):
        return "//*[contains(@resource-id, 'select_button_tap_target')]"

    @property
    def audio_scrubber_view(self):
        return "//*[contains(@resource-id, 'scrubber_recycler_view')]"

    @property
    def home_feed_ready_identifier(self):
        return '//android.widget.Button[@content-desc="Instagram Home Feed"]'

    @property
    def reel_creation_tab_general(self):
        return "//*[contains(@text, 'REEL') or contains(@content-desc, 'REEL')]"

    @property
    def new_reel_screen_identifier_general(self):
        return "//*[contains(@text, 'New reel') or contains(@content-desc, 'New reel')]"

    @property
    def final_share_or_next_button(self):
        return "//*[contains(@text, 'Next') or contains(@content-desc, 'Next') or contains(@content-desc, 'Share')]"

    @property
    def back_button(self):
        return "//*[@content-desc='Back']"

    @property
    def search_layout_container_frame(self):
        return "//android.widget.FrameLayout"

    @property
    def search_layout_container_rid_pattern(self):
        return "^.*layout_container$"

    @property
    def search_image_post_button(self):
        return ".//android.widget.Button"

    @property
    def search_reel_imageview(self):
        return ".//android.widget.ImageView"

    @property
    def search_reel_imageview_template(self):
        return '//android.widget.ImageView[@content-desc="{}"]'

    @property
    def reel_profile_picture_desc_contains(self):
        return (
            '//android.widget.ImageView[contains(@content-desc, "Profile picture of")]'
        )

    @property
    def reel_caption_container(self):
        return f'//android.view.ViewGroup[@resource-id="{self.package_name}:id/clips_caption_component"]//android.view.ViewGroup[contains(@content-desc, "")]'

    @property
    def reel_likes_button_desc(self):
        return '//android.view.ViewGroup[contains(@content-desc, "View likes")]'

    @property
    def reel_reshare_button_desc(self):
        return '//android.view.ViewGroup[contains(@content-desc, "Reshare number")]'

    @property
    def reel_audio_link_desc_contains(self):
        return '//android.view.ViewGroup[contains(@content-desc, "Original audio")]'

    @property
    def reel_follow_button_text(self):
        return '//android.widget.Button[@text="Follow"]'

    @property
    def reel_like_or_unlike_button_desc(self):
        return '//*[@content-desc="Like" or @content-desc="Unlike"]'

    @property
    def search_posts_section_title(self):
        return f'//*[@resource-id="{self.package_name}:id/title_text_view" and @text="Posts"]'

    @property
    def search_results_recycler_view(self):
        return "//*[contains(@resource-id, 'recycler_view')]"

    # --- END: Existing XPaths from your provided class ---

    # --- START: NEW XPaths specific to Reel Editing Flow (based on your list) ---
    @property
    def reel_edit_creation_toolbar_recyclerview(self):
        """The main toolbar on the reel editing page containing icons for various tools."""
        return f"//androidx.recyclerview.widget.RecyclerView[@resource-id='{self.package_name}:id/creation_toolbar_recyclerview']"

    @property
    def reel_edit_toolbar_add_audio_button(
        self,
    ):  # Specifically for toolbar context, if different from general 'add_sound'
        """'Add audio' button within the creation_toolbar_recyclerview."""
        # This is often identified by its content-desc within the toolbar.
        return f"//android.widget.LinearLayout[@content-desc='Add audio']"  # As per your list

    @property
    def reel_edit_initial_add_text_button(self):
        """The initial button to click to start adding text (e.g., 'Aa' icon or text)."""
        # Based on your flow "We click add text" - assuming a primary button for this.
        # Your list doesn't have a direct one, I'll use the common TextView version.
        return "//android.widget.TextView[@content-desc='Add text']"  # Verify this element type and desc

    @property
    def reel_edit_text_input_field_focused(self):
        """The EditText field that is focused and ready for text input after clicking 'Add Text'."""
        # This is crucial but often lacks a unique static ID. @focused='true' is a good strategy.
        # return f"//android.widget.EditText[@focused='true']"
        # Or if it's always the only EditText within a specific container:
        return f"//android.widget.EditText"  # Generic, assuming it's the one active after "Add Text"

    @property
    def reel_edit_text_tool_menu_group(self):
        """The LinearLayout group containing buttons for font, color, animation, etc., for the text tool."""
        return f"//android.widget.LinearLayout[@resource-id='{self.package_name}:id/postcapture_text_tool_menu_button_group']"

    @property
    def reel_edit_text_font_category_button(self):
        """Button within text tool menu to open font styles (e.g., an 'A' icon)."""
        # This would be a child of reel_edit_text_tool_menu_group.
        # You need to inspect its actual type (e.g., ImageView) and content-desc or index.
        # Example: return f"{self.reel_edit_text_tool_menu_group}/android.widget.ImageView[@content-desc='Font style']"
        # For now, assuming a generic first clickable element if no specific desc:
        return f"({self.reel_edit_text_tool_menu_group}//android.widget.ImageView)[1]"  # Placeholder: First ImageView

    @property
    def reel_edit_text_font_styles_scrollable(self):
        """The scrollable container (e.g., HorizontalScrollView) holding individual font style previews."""
        # This is where font names like "Typewriter", "Classic" are listed and swiped.
        # Needs to be identified by inspecting the UI when font styles are visible.
        # Example: return f"//android.widget.HorizontalScrollView[contains(@resource-id,'font_picker')]"
        return f"//android.widget.HorizontalScrollView"  # Placeholder: a generic scroll view, needs to be specific

    @property
    def reel_edit_text_font_stroke_width_tool(self):
        """Button or View for 'Stroke width tool' (font size/style adjustment)."""
        return f"//android.view.View[@content-desc='Stroke width tool']"

    @property
    def reel_edit_text_color_category_button(self):
        """Button within text tool menu to open color picker."""
        # Similar to font_category_button, needs inspection.
        # Example: return f"{self.reel_edit_text_tool_menu_group}/android.widget.ImageView[@content-desc='Color']"
        return f"({self.reel_edit_text_tool_menu_group}//android.widget.ImageView)[2]"  # Placeholder: Second ImageView

    def reel_edit_text_color_option(self, color_name: str):
        """Template for a specific color option button, e.g., 'Black color'."""
        return f"//android.view.View[@content-desc='{color_name} color']"

    @property
    def reel_edit_text_animation_icon(
        self,
    ):  # This is the icon to open the animations panel
        """ImageView icon that opens the text animation selection panel."""
        return f"//android.widget.ImageView[@content-desc='Text animation']"

    @property
    def reel_edit_text_animation_picker_recyclerview(self):
        """RecyclerView that lists available text animations."""
        return f"//androidx.recyclerview.widget.RecyclerView[@resource-id='{self.package_name}:id/text_tool_animation_picker_recycler_view']"

    def reel_edit_text_animation_style_button(self, animation_name: str):
        """Template for a button representing a specific text animation style."""
        return f"//android.widget.Button[@content-desc='{animation_name} text animation style']"

    @property
    def reel_edit_text_background_effect_category_button(self):
        """Button within text tool menu to open text background effects (your "Text Effect")."""
        # Example: return f"{self.reel_edit_text_tool_menu_group}/android.widget.ImageView[@content-desc='Background Effect']"
        return f"({self.reel_edit_text_tool_menu_group}//android.widget.ImageView)[3]"  # Placeholder: Third ImageView

    @property
    def reel_edit_text_effect_picker_recyclerview(self):  # Your "Text Effect" list
        """RecyclerView that lists available text background effects."""
        return f"//androidx.recyclerview.widget.RecyclerView[@resource-id='{self.package_name}:id/text_tool_effect_picker_recycler_view']"

    @property
    def reel_edit_text_no_effect_button(self):
        """Button for 'No text effect style' (for text background effects)."""
        return f"//android.widget.Button[@content-desc='No text effect style']"

    def reel_edit_text_effect_style_button(self, effect_name: str):
        """Template for a button representing a specific text background effect style."""
        return (
            f"//android.widget.Button[@content-desc='{effect_name} text effect style']"
        )

    def reel_edit_text_alignment_button(self, alignment: str = "center"):
        """Template for the text alignment button (e.g., 'Text alignment center')."""
        return f"//android.widget.ImageView[@content-desc='Text alignment {alignment}']"

    @property
    def reel_edit_text_tool_done_button(self):
        """The 'Done' button within the text editing tool to apply text and close the tool."""
        # Your list has: //android.widget.Button[@content-desc="Done"]
        # This is distinct from the general 'click_done' or 'reel_tag_people_done_button'
        return f"//android.widget.Button[@content-desc='Done' and ancestor::*[@resource-id='{self.package_name}:id/postcapture_text_tool_menu_button_group']]"  # More specific if possible
        # If the simple content-desc is unique enough when text tool is active:
        # return f"//android.widget.Button[@content-desc='Done']" # As per your list, assuming context makes it unique

    @property
    def reel_edit_page_next_button(self):
        """The main 'Next' button on the reel editing page to proceed to the share/caption screen."""
        # Your list implies "Then click next" after all text edits are done and its specific "Done" is clicked.
        # This should be the same as your general 'next_button' if its content-desc is "Next".
        return f'//android.widget.Button[@content-desc="Next"]'

    # --- Stickers ---
    @property
    def reel_edit_add_sticker_button(self):
        """Button to add a sticker to the reel."""
        return f"//android.widget.Button[@content-desc='Add sticker']"

    @property
    def reel_edit_sticker_asset_picker_container(self):
        """The main FrameLayout container for the sticker picker/tray."""
        # Your list has: /android.widget.FrameLayout[@resource-id="...:id/asset_picker_container"]
        # Using // for more robustness:
        return f"//android.widget.FrameLayout[@resource-id='{self.package_name}:id/asset_picker_container']"

    @property
    def reel_edit_sticker_asset_picker(self):
        """LinearLayout representing the asset picker itself within the container."""
        return f"//android.widget.LinearLayout[@resource-id='{self.package_name}:id/asset_picker']"

    @property
    def reel_edit_sticker_items_container(self):
        """FrameLayout containing the actual sticker items/previews."""
        return f"//android.widget.FrameLayout[@resource-id='{self.package_name}:id/asset_items_container']"

    @property
    def reel_edit_sticker_drag_chevron(self):
        """ImageView for the drag chevron, possibly for sticker tray interaction."""
        return f"//android.widget.ImageView[@resource-id='{self.package_name}:id/drag_chevron']"

    @property
    def reel_edit_sticker_search_bar_edittext(
        self,
    ):  # Changed to target EditText directly
        """The EditText field within the sticker search bar container."""
        return f"//android.widget.LinearLayout[@resource-id='{self.package_name}:id/search_bar_container']//android.widget.EditText"

    @property
    def reel_edit_sticker_list_recyclerview(self):
        """The RecyclerView for sticker lists (often with resource-id 'list')."""
        return f"//androidx.recyclerview.widget.RecyclerView[@resource-id='{self.package_name}:id/list']"

    def reel_edit_sticker_list_item_by_index(
        self, index: int
    ):  # XPath indices are 1-based
        """Gets a sticker list item (LinearLayout) by its 1-based index from reel_edit_sticker_list_recyclerview."""
        return f"({self.reel_edit_sticker_list_recyclerview}/android.widget.LinearLayout)[{index}]"

    # --- Main Video Effects ---
    @property
    def reel_edit_effects_button(self):
        """Main 'Effects' button on the reel editing screen for video effects."""
        return f"//android.widget.Button[@content-desc='Effects']"

    @property
    def reel_edit_effect_apply_no_effect_button(self):
        """Button to apply 'No effect' for video effects."""
        return f"//android.widget.Button[@content-desc='Apply effect No effect']"

    @property
    def reel_edit_effects_gridview(self):
        """GridView containing video effect previews."""
        return f"//android.widget.GridView[@resource-id='{self.package_name}:id/camera_effect_preview_video_recycler_view']"

    def reel_edit_effect_apply_button_by_name(self, effect_name: str):
        """Template for a specific video effect button, e.g., 'Apply effect Cinematic 𝐇𝐃'."""
        return f"//android.widget.Button[@content-desc='Apply effect {effect_name}']"

    @property
    def reel_edit_effects_bottom_sheet_drag_handle(self):
        """Drag handle (prism) to close the video effects menu/bottom sheet."""
        return f"//android.widget.ImageView[@resource-id='{self.package_name}:id/bottom_sheet_drag_handle_prism']"

    # --- Caption Page Add-ons (Hashtags, Poll) ---
    @property
    def reel_caption_page_add_ons_recyclerview(self):
        """RecyclerView on the caption/share page for add-ons like Hashtags, Poll."""
        return f"//androidx.recyclerview.widget.RecyclerView[@resource-id='{self.package_name}:id/caption_add_on_recyclerview']"

    @property
    def reel_caption_page_hashtags_button(self):
        """Hashtags button on the caption page (first LinearLayout in add_ons_recyclerview)."""
        return f"{self.reel_caption_page_add_ons_recyclerview}/android.widget.LinearLayout[1]"

    @property
    def reel_caption_page_poll_button(self):
        """Poll button on the caption page (second LinearLayout in add_ons_recyclerview)."""
        return f"{self.reel_caption_page_add_ons_recyclerview}/android.widget.LinearLayout[2]"

    # --- Tag People ---
    @property
    def reel_edit_tag_people_button(self):  # Changed from _from_toolbar for clarity
        """The 'Tag people' button on the main reel editing screen."""
        # Prioritizing the more specific text-based XPath from your list:
        return f"//android.widget.TextView[@resource-id='{self.package_name}:id/title' and @text='Tag people']"
        # Fallback from your list (less robust):
        # return f"//android.widget.LinearLayout[@resource-id='{self.package_name}:id/content_view']/android.widget.Button[1]"

    @property
    def reel_tag_people_add_tag_button(self):
        """Button to 'Add Tag' on the Tag People screen after clicking a user."""
        return f"//android.widget.FrameLayout[@resource-id='{self.package_name}:id/add_people_tag_button']"

    @property
    def reel_tag_people_search_bar_edittext(self):
        """EditText field for searching users to tag."""
        return f"//android.widget.EditText[@content-desc='Search for a user']"

    @property
    def reel_tag_people_search_results_listview(self):
        """ListView containing the search results when tagging people."""
        return f"//android.widget.ListView[@resource-id='android:id/list']"  # Uses 'android' namespace

    def reel_tag_people_search_result_user_container_by_index(
        self, index: int
    ):  # 1-based index for XPath
        """A specific user container (Button) in tag search results by its 1-based index."""
        return f"({self.reel_tag_people_search_results_listview}//android.widget.Button[@resource-id='{self.package_name}:id/row_search_user_container'])[{index}]"

    def reel_tag_people_search_result_user_container_by_username(self, username: str):
        """Finds a user container in tag search results by their exact username text."""
        # Ensure username doesn't contain single quotes or escape them properly for XPath.
        safe_username = username.replace("'", "\\'")
        return f"{self.reel_tag_people_search_results_listview}//android.widget.Button[@resource-id='{self.package_name}:id/row_search_user_container' and .//android.widget.TextView[@resource-id='{self.package_name}:id/row_search_user_username' and @text='{safe_username}']]"

    @property
    def reel_tag_people_username_in_result(self):
        """Relative XPath for the TextView containing the username within a search result item."""
        return f".//android.widget.TextView[@resource-id='{self.package_name}:id/row_search_user_username']"

    @property
    def reel_tag_people_fullname_in_result(self):
        """Relative XPath for the TextView containing the full name within a search result item."""
        return f".//android.widget.TextView[@resource-id='{self.package_name}:id/row_search_user_fullname']"

    @property
    def reel_tag_people_done_button(self):
        """The 'Done' button specifically for the Tag People screen."""
        # Your list has: //android.widget.Button[@content-desc="Done"]
        # This needs to be distinguished from other "Done" buttons if the content-desc is identical.
        # Assuming context (being on the tag people screen) makes it unique, or a more specific parent exists.
        return f"//android.widget.Button[@content-desc='Done']"  # As per your list, assuming context makes it unique

    # --- END: NEW XPaths specific to Reel Editing Flow ---


class FirefoxEmailXPaths:
    """
    Contains XPath selectors specifically for automating Firefox and the op.pl email interface.
    NOTE: These are highly specific to the observed UI and likely to break if the UI changes.
    """

    def __init__(
        self, firefox_package="org.mozilla.firefox"
    ):  # Corrected package name example
        # Using firefox_package might not be necessary if IDs are stable, but kept for consistency
        self.firefox_package = firefox_package

    # --- Firefox Browser UI ---
    @property
    def firefox_url_bar_smart_search(self):
        """Smart search text often present in the URL bar."""
        # From FirefoxSession._launch_firefox
        return "^Search or enter address"

    @property
    def firefox_url_bar_edit_text(self):
        """EditText element for the URL bar (fallback)."""
        # From FirefoxSession._launch_firefox and _navigate_to_url
        # Consider making the resource-id part more robust if it changes
        return '//android.widget.EditText[contains(@resource-id, "edit_url_view")]'

    @property
    def firefox_tabs_button(self):
        """Button to view open tabs."""
        # From EmailNavigation.open_new_tab
        return '//android.widget.ImageView[@content-desc="Tabs"]'

    @property
    def firefox_new_tab_button(self):
        """Button/TextView to open a new tab from the tabs view."""
        # From EmailNavigation.open_new_tab
        return '//android.widget.TextView[contains(@text, "New tab")]'

    # --- op.pl Email Login UI ---
    @property
    def email_login_email_field(self):
        """Email input field on the login page."""
        # From EmailLogin.handle_email_input
        return '//android.widget.EditText[@resource-id="email"]'

    @property
    def email_login_password_field(self):
        """Password input field on the login page."""
        # From EmailLogin.handle_email_input and handle_password_input
        return '//android.widget.EditText[@resource-id="password"]'

    @property
    def email_login_next_button_text(self):
        """Text for the 'NEXT' button after entering email."""
        # From EmailLogin.handle_email_input (used in smart_button_clicker)
        return "NEXT"

    @property
    def email_login_next_button_fallback(self):
        """Fallback XPath for the 'NEXT' button."""
        # From EmailLogin.handle_email_input (used in smart_button_clicker)
        return '//android.widget.Button[@text="NEXT"]'

    @property
    def email_login_login_button_text(self):
        """Text for the 'LOG IN' button after entering password."""
        # From EmailLogin.handle_password_input (used in smart_button_clicker)
        return "LOG IN"

    @property
    def email_login_login_button_fallback(self):
        """Fallback XPath for the 'LOG IN' button."""
        # From EmailLogin.handle_password_input (used in smart_button_clicker)
        return '//android.widget.Button[@text="LOG IN"]'

    # --- op.pl Email Inbox/Content UI ---
    @property
    def email_main_container(self):
        """Main container element indicating successful login/inbox view."""
        # From EmailNavigation.verify_logged_in
        return "^React_MainContainer"  # Smart search by resource-id end

    @property
    def email_instagram_verification_block(self):
        """XPath to find the container block for an Instagram verification email preview."""
        # From EmailNavigation.find_code_in_main_container
        # This is complex and highly dependent on the specific email client's web UI structure.
        return (
            '//android.view.View[@resource-id="React_MainContainer"]'
            '//android.view.View[.//android.view.View[@text="Instagram"] and .//android.view.View[@text="Verify your account"]]'
        )

    @property
    def email_instagram_sender_text(self):
        """XPath to find the 'Instagram' sender text within an email block/preview."""
        # Used implicitly in email_instagram_verification_block logic, defining explicitly
        return './/android.view.View[@text="Instagram"]'  # Relative search

    @property
    def email_instagram_subject_text(self):
        """XPath to find the 'Verify your account' subject text within an email block/preview."""
        # Used implicitly in email_instagram_verification_block logic, defining explicitly
        return './/android.view.View[@text="Verify your account"]'  # Relative search

    @property
    def email_opened_content_container(self):
        """XPath for the container holding the full content of an opened email."""
        # From EmailNavigation._open_email_and_extract_code and TwoFactorTokenRetriever.wait_for_email_content
        # WARNING: This XPath is extremely long and fragile, based on nested GridViews.
        # It's highly likely to break. Finding a more stable identifier is recommended.
        return (
            '//android.view.View[@resource-id="email_content"]'
            "/android.widget.GridView/android.view.View[4]/android.view.View"
            "/android.widget.GridView/android.view.View/android.view.View"
            "/android.widget.GridView/android.view.View[2]/android.view.View"
            "/android.widget.GridView/android.view.View/android.view.View"
            "/android.widget.GridView/android.view.View"
            "/android.view.View[2]/android.widget.GridView/android.view.View/android.view.View"
        )  # Simplified slightly if possible

    @property
    def email_opened_verification_code(self):
        """XPath to find a 6-digit code within the opened email content."""
        # From EmailNavigation._open_email_and_extract_code and TwoFactorTokenRetriever.extract_verification_code
        # This uses XPath functions for validation.
        return '//android.view.View[string-length(@text)=6 and translate(@text, "0123456789", "") = ""]'

    @property
    def email_sidebar_button(self):
        """Button to open the sidebar/menu in the email client."""
        # From EmailNavigation.open_sidebar
        return '//android.widget.Button[@resource-id="sidebar-btn"]'

    @property
    def email_sidebar_write_message_button(self):
        """'Write message' button inside the sidebar (used to verify sidebar is open)."""
        # From EmailNavigation.verify_sidebar_open
        return '//android.widget.Button[@text="Napisz wiadomość"]'  # Text is language-specific

    @property
    def email_sidebar_communities_button(self):
        """'Communities' button/view inside the sidebar."""
        # From EmailNavigation.navigate_to_communities
        return '//android.view.View[contains(@text, "Społeczności")]'  # Text is language-specific

    @property
    def email_account_menu_button(self):
        """Button to open the user account menu (for logout)."""
        # From EmailNavigation.logout_of_email
        return '//android.widget.Button[@text="Menu użytkownika"]'  # Text is language-specific

    @property
    def email_logout_button(self):
        """Logout button/view within the account menu."""
        # From EmailNavigation.logout_of_email
        return '//android.view.View[contains(@text, "Wyloguj") or contains(@content-desc, "Sign out")]'  # Text is language-specific


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
