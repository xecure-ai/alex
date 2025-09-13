import Layout from "../components/Layout";

export default function Accounts() {
  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-2xl font-bold text-dark mb-4">Investment Accounts</h2>
          <p className="text-gray-600 mb-6">
            Manage your investment accounts and track your positions.
          </p>

          <div className="bg-primary/10 border border-primary/20 rounded-lg p-4">
            <p className="text-primary font-semibold">
              Your accounts will appear here
            </p>
            <p className="text-sm text-gray-600 mt-2">
              You'll be able to add and manage your 401(k), IRA, and brokerage accounts.
            </p>
          </div>
        </div>
      </div>
    </Layout>
  );
}