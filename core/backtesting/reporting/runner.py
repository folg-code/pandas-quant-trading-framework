class ReportRunner:
    def __init__(self, reports):
        self.reports = reports

    def run(self):
        for report in self.reports:
            report.run()