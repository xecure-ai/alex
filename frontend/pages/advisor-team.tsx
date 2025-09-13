import Layout from "../components/Layout";

export default function AdvisorTeam() {
  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-2xl font-bold text-dark mb-4">Your AI Advisor Team</h2>
          <p className="text-gray-600 mb-6">
            Meet your specialized AI agents that work together to analyze your portfolio.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Planner Agent */}
            <div className="bg-ai-accent/10 border border-ai-accent/20 rounded-lg p-4">
              <h3 className="text-lg font-semibold text-ai-accent mb-2">
                🎯 Financial Planner
              </h3>
              <p className="text-sm text-gray-600">
                Coordinates your financial analysis and delegates to specialized agents.
              </p>
            </div>

            {/* Reporter Agent */}
            <div className="bg-primary/10 border border-primary/20 rounded-lg p-4">
              <h3 className="text-lg font-semibold text-primary mb-2">
                📊 Portfolio Analyst
              </h3>
              <p className="text-sm text-gray-600">
                Analyzes your holdings and performance to generate detailed reports.
              </p>
            </div>

            {/* Charter Agent */}
            <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-4">
              <h3 className="text-lg font-semibold text-green-600 mb-2">
                📈 Chart Specialist
              </h3>
              <p className="text-sm text-gray-600">
                Visualizes your portfolio composition with interactive charts.
              </p>
            </div>

            {/* Retirement Agent */}
            <div className="bg-accent/10 border border-accent/20 rounded-lg p-4">
              <h3 className="text-lg font-semibold text-accent mb-2">
                🎯 Retirement Planner
              </h3>
              <p className="text-sm text-gray-600">
                Projects your retirement readiness with Monte Carlo simulations.
              </p>
            </div>
          </div>

          <div className="mt-6 text-center">
            <button className="px-8 py-3 bg-ai-accent text-white font-semibold rounded-lg hover:bg-purple-700 transition-colors">
              Start New Analysis
            </button>
          </div>
        </div>
      </div>
    </Layout>
  );
}