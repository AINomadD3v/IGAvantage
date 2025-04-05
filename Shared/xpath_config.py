# xpath_config.py

class InstagramXPaths:
    def __init__(self, package_name='com.instagram.androie'):
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
        return "//android.widget.ImageView[contains(@content-desc, \"'s story at column\")]"

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
        return  f"//android.widget.EditText"

    @property
    def confirmation_code_input(self):
        return  f"//android.widget.EditText"
    
    @property
    def click_select_song(self):
        """The click_select_song property."""
        return f"//android.widget.FrameLayout[@resource-id='{self.package_name}:id/select_button_tap_target']"

