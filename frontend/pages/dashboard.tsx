import { useUser, UserButton, Protect, useAuth } from "@clerk/nextjs";
import { useRouter } from "next/router";
import { useEffect, useState } from "react";

export default function Dashboard() {
  const { user, isLoaded: userLoaded } = useUser();
  const { getToken } = useAuth();
  const router = useRouter();
  const [userData, setUserData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function syncUser() {
      if (!userLoaded || !user) return;

      try {
        const token = await getToken();
        if (!token) {
          setError("Not authenticated");
          setLoading(false);
          return;
        }

        // Call the API to get/create user
        const response = await fetch("http://localhost:8000/api/user", {
          headers: {
            "Authorization": `Bearer ${token}`,
          },
        });

        if (!response.ok) {
          throw new Error(`Failed to sync user: ${response.status}`);
        }

        const data = await response.json();
        setUserData(data);
        console.log("User synced:", data);
      } catch (err) {
        console.error("Error syncing user:", err);
        setError(err instanceof Error ? err.message : "Failed to sync user");
      } finally {
        setLoading(false);
      }
    }

    syncUser();
  }, [userLoaded, user, getToken]);

  return (
    <Protect fallback={<div className="min-h-screen flex items-center justify-center">Redirecting to sign in...</div>}>
      <div className="min-h-screen bg-gray-50">
        {/* Navigation */}
        <nav className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <h1 className="text-xl font-bold text-dark">
                Alex <span className="text-primary">AI Financial Advisor</span>
              </h1>
            </div>
            <div className="flex items-center gap-6">
              <span className="text-sm text-gray-600">
                Welcome, {user?.firstName || user?.emailAddresses[0]?.emailAddress}
              </span>
              <UserButton afterSignOutUrl="/" />
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-2xl font-bold text-dark mb-4">Dashboard</h2>
          <p className="text-gray-600 mb-6">
            Welcome to your AI-powered financial advisor dashboard. Your portfolio analysis features are coming soon!
          </p>
          
          <div className="bg-ai-accent/10 border border-ai-accent/20 rounded-lg p-4">
            <p className="text-ai-accent font-semibold">
              🎯 Your AI advisory team is ready to analyze your portfolio
            </p>
            <p className="text-sm text-gray-600 mt-2">
              Once the backend is connected, you'll be able to:
            </p>
            <ul className="list-disc list-inside text-sm text-gray-600 mt-2 space-y-1">
              <li>Add your investment accounts</li>
              <li>Track your portfolio performance</li>
              <li>Get AI-powered analysis and recommendations</li>
              <li>View retirement projections</li>
            </ul>
          </div>

          <div className="mt-6 p-4 bg-gray-50 rounded-lg">
            <p className="text-sm text-gray-500">
              Clerk User ID: {user?.id}
            </p>
            <p className="text-sm text-gray-500">
              Email: {user?.emailAddresses[0]?.emailAddress}
            </p>
            {loading ? (
              <p className="text-sm text-gray-500 mt-2">Syncing with backend...</p>
            ) : error ? (
              <p className="text-sm text-red-500 mt-2">Error: {error}</p>
            ) : userData ? (
              <>
                <p className="text-sm text-green-600 mt-2">
                  ✅ User synced {userData.created ? "(newly created)" : "(existing user)"}
                </p>
                <p className="text-sm text-gray-500 mt-1">
                  Database ID: {userData.user?.id}
                </p>
                <p className="text-sm text-gray-500">
                  Years until retirement: {userData.user?.years_until_retirement}
                </p>
              </>
            ) : null}
          </div>
        </div>
      </main>
    </div>
    </Protect>
  );
}