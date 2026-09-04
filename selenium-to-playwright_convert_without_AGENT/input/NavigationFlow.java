public class NavigationFlow {
    public void navigate(WebDriver driver) {
        driver.get("https://example.test");
        driver.navigate().refresh();
        driver.navigate().back();
        driver.navigate().forward();
    }
}