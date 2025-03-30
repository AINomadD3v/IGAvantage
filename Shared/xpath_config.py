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
        return f"//android.widget.Button[@content-desc='Next']"

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
    def video_thumbnails(self):
        return f"//android.widget.GridView[@resource-id='{self.package_name}:id/gallery_recycler_view']/android.view.ViewGroup[1]"

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
        return f"//android.widget.Button[@content-desc='Add audio']"

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

class GmailXPaths:
    def __init__(self, package_name='com.android.chromz'):
        self.package_name = package_name
    
    # Chrome initial setup popups
    @property
    def allow_button(self):
        return '//android.widget.Button[@resource-id="com.android.permissioncontroller:id/permission_allow_button"]'

    @property
    def alert_title(self):
        return '//android.widget.TextView[@resource-id="android:id/alertTitle"]'

    @property
    def alert_button(self):
        return '//android.widget.Button[@resource-id="android:id/button1"]'

    @property
    def permission_icon(self):
        return '//android.widget.ImageView[@resource-id="com.android.permissioncontroller:id/permission_icon"]'

    @property
    def permission_allow(self):
        return '//android.widget.Button[@resource-id="com.android.permissioncontroller:id/permission_allow_button"]'

    @property
    def use_account_page(self):
        return f'//android.widget.TextView[@resource-id="{self.package_name}:id/title"]'

    @property
    def use_without_account(self):
        return f'//android.widget.Button[@resource-id="{self.package_name}:id/signin_fre_dismiss_button"]'
    
    @property
    def enhanced_ad_privacy(self):
        return '//android.widget.TextView[@text="Enhanced ad privacy in Chrome"]'


    @property
    def got_it(self):
        return f'//android.widget.Button[@resource-id="{self.package_name}:id/ack_button"]'

    @property
    def home_page(self):
        return f'//android.widget.FrameLayout[@resource-id="{self.package_name}:id/search_provider_logo"]'
    
    # Navigation elements
    @property
    def url_bar(self):
        return f'//android.widget.EditText[@resource-id="{self.package_name}:id/url_bar"]'
    
    @property
    def menu_button(self):
        return f'//android.widget.ImageButton[@content-desc="Customize and control Google Chrome"]'

    @property
    def new_incognito_tab(self):
        return f'//android.widget.LinearLayout[@resource-id="{self.package_name}:id/new_incognito_tab_menu_id"]'
    
    @property
    def confirm_not_robot(self):
        return f'//android.widget.TextView[@text="Confirm you’re not a robot"]'

    @property
    def click_not_robot(self):
        return f'//android.widget.CheckBox[@resource-id="recaptcha-anchor"]'

    # Gmail login elements

    @property
    def sign_in_text(self):
        return '//android.widget.TextView[@text="Sign in"]'
    
    @property
    def email_input(self):
        return '//android.webkit.WebView[@text="Gmail"]/android.view.View/android.view.View[1]/android.view.View/android.view.View[1]/android.view.View/android.view.View[1]/android.view.View/android.widget.EditText'
    
    # @property
    # def next_button(self):
    #     return '//android.widget.Button[@text="Next"]'
    
    @property
    def welcome_text(self):
        return '//android.widget.TextView[@text="Welcome"]'
    
    @property
    def password_input(self):
        return '//android.view.View[@resource-id="password"]/android.view.View/android.view.View/android.widget.EditText'
    
    # Recovery email elements
    @property
    def recovery_email_button(self):
        return '//android.view.View[@content-desc="Confirm your recovery email"]'
    
    @property
    def recovery_email_input(self):
        return '//android.widget.EditText[@resource-id="knowledge-preregistered-email-response"]'
    
    # Post-login elements
    @property
    def signed_in_message(self):
        return '//android.webkit.WebView[@text="Google Account"]/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View[1]'
    
    @property
    def not_now_button(self):
        return '//android.widget.Button[@text="Not now"]'
    
    @property
    def use_web_version(self):
        return '//android.widget.TextView[@text="Use the web version"]'
    
    @property
    def open_app_button(self):
        return '//android.widget.Button[@text="OPEN THE GMAIL APP"]'
    
    # Instagram verification code elements
    @property
    def instagram_verification_email(self):
        return '//android.widget.Button[contains(@text, "Unread. instagram") and contains(@text, "is your instagram confirmation code")]'

