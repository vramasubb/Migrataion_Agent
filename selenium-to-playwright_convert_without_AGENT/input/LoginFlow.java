import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;

public class LoginFlow {
    private By username = By.id("user-name");
    private By loginButton = By.id("login-button");

    public void login(WebDriver driver) {
        driver.get("https://www.saucedemo.com");
        username.sendKeys("standard_user");
        loginButton.click();
        assertTrue(loginButton.isDisplayed());
    }
}