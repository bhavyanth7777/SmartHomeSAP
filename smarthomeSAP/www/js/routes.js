Path.map("#/dashboard").to(function () {
    $("#stage").load("screens/dashboard.html");
});

Path.map("#/dashboardSleep").to(function () {
    $("#stage").load("screens/dashboardSleep.html");
});

Path.map("#/dashboardPulse").to(function () {
    $("#stage").load("screens/dashboardPulse.html");
});


Path.root("#/dashboard");
Path.listen();
