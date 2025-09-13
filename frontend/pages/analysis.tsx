import Layout from "../components/Layout";

export default function Analysis() {
  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-2xl font-bold text-dark mb-4">Portfolio Analysis</h2>
          <p className="text-gray-600 mb-6">
            View your AI-generated portfolio analysis and recommendations.
          </p>

          <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center">
            <p className="text-gray-500 text-lg mb-4">
              No analysis available yet
            </p>
            <p className="text-sm text-gray-400 mb-6">
              Run an analysis from the Advisor Team page to see your results here.
            </p>
            <button
              onClick={() => window.location.href = '/advisor-team'}
              className="px-6 py-2 bg-primary text-white font-medium rounded-lg hover:bg-blue-600 transition-colors"
            >
              Go to Advisor Team
            </button>
          </div>
        </div>
      </div>
    </Layout>
  );
}