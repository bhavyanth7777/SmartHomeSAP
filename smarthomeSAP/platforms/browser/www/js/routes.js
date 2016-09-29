Path.map("#/dashboard").to(function () {
    $("#stage").load("screens/dashboard.html");
});

Path.map("#/dashboardSleep").to(function () {
    $("#stage").load("screens/dashboardSleep.html");
});

Path.map("#/dashboardPulse").to(function () {
    $("#stage").load("screens/dashboardPulse.html");
});

Path.map("#/caregiverprofile").to(function () {
    $("#stage").load("screens/caregiverprofile.html");
});

Path.map("#/sensors").to(function () {
    $("#stage").load("screens/configureSensors.html");
});

Path.map("#/alerts").to(function () {
    $("#stage").load("screens/configureAlerts.html");
});


Path.root("#/dashboard");
Path.listen();
