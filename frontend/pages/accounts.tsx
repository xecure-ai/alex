import { useAuth } from "@clerk/nextjs";
import { useState, useEffect, useCallback } from "react";
import Layout from "../components/Layout";

interface Position {
  id: string;
  symbol: string;
  quantity: number;
  current_price?: number;
}

interface Account {
  id: string;
  account_name: string;
  account_purpose: string;
  cash_balance: number;
  positions?: Position[];
}

export default function Accounts() {
  const { getToken } = useAuth();
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [populatingData, setPopulatingData] = useState(false);
  const [resettingAccounts, setResettingAccounts] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

  const loadAccounts = useCallback(async () => {
    try {
      const token = await getToken();
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/accounts`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        console.log('Accounts received from API:', data);
        // For each account, load positions
        const accountsWithPositions = await Promise.all(
          data.map(async (account: Account) => {
            console.log('Processing account:', account.id, account.account_name);
            // Skip if account has no ID
            if (!account.id) {
              console.warn('Account missing ID:', account);
              return { ...account, positions: [] };
            }

            try {
              const positionsResponse = await fetch(
                `${process.env.NEXT_PUBLIC_API_URL}/api/accounts/${account.id}/positions`,
                {
                  headers: {
                    'Authorization': `Bearer ${token}`,
                  },
                }
              );
              if (positionsResponse.ok) {
                const positions = await positionsResponse.json();
                console.log(`Loaded ${positions.length} positions for account ${account.id}`);
                return { ...account, positions };
              }
            } catch (err) {
              console.error(`Error loading positions for account ${account.id}:`, err);
            }
            return { ...account, positions: [] };
          })
        );
        console.log('Final accounts with positions:', accountsWithPositions);
        setAccounts(accountsWithPositions);
      }
    } catch (error) {
      console.error('Error loading accounts:', error);
      setMessage({ type: 'error', text: 'Failed to load accounts' });
    } finally {
      setLoading(false);
    }
  }, [getToken]);

  useEffect(() => {
    loadAccounts();
  }, [loadAccounts]);

  const populateTestData = async () => {
    setPopulatingData(true);
    setMessage(null);

    try {
      const token = await getToken();
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/populate-test-data`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        setMessage({ type: 'success', text: data.message });
        await loadAccounts(); // Reload accounts after population
      } else {
        setMessage({ type: 'error', text: 'Failed to populate test data' });
      }
    } catch (error) {
      console.error('Error populating test data:', error);
      setMessage({ type: 'error', text: 'Error populating test data' });
    } finally {
      setPopulatingData(false);
    }
  };

  const resetAccounts = async () => {
    if (!confirm('Are you sure you want to delete all your accounts? This action cannot be undone.')) {
      return;
    }

    setResettingAccounts(true);
    setMessage(null);

    try {
      const token = await getToken();
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/reset-accounts`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setMessage({ type: 'success', text: data.message });
        // Clear accounts immediately after successful reset
        setAccounts([]);
        // Then reload to confirm empty state
        await loadAccounts();
      } else {
        setMessage({ type: 'error', text: 'Failed to reset accounts' });
      }
    } catch (error) {
      console.error('Error resetting accounts:', error);
      setMessage({ type: 'error', text: 'Error resetting accounts' });
    } finally {
      setResettingAccounts(false);
    }
  };

  const calculateAccountTotal = (account: Account) => {
    const positionsValue = account.positions?.reduce((sum, position) => {
      const value = Number(position.quantity) * (Number(position.current_price) || 0);
      return sum + value;
    }, 0) || 0;
    return Number(account.cash_balance) + positionsValue;
  };

  const calculatePortfolioTotal = () => {
    return accounts.reduce((sum, account) => sum + calculateAccountTotal(account), 0);
  };

  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-bold text-dark">Investment Accounts</h2>
            <div className="flex gap-2">
              {accounts.length === 0 && !loading && (
                <button
                  onClick={populateTestData}
                  disabled={populatingData}
                  className="bg-accent hover:bg-yellow-600 text-white px-4 py-2 rounded-lg transition-colors disabled:opacity-50"
                >
                  {populatingData ? 'Populating...' : 'Populate Test Data'}
                </button>
              )}
              {accounts.length > 0 && (
                <button
                  onClick={resetAccounts}
                  disabled={resettingAccounts}
                  className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg transition-colors disabled:opacity-50"
                >
                  {resettingAccounts ? 'Resetting...' : 'Reset Accounts'}
                </button>
              )}
            </div>
          </div>

          {message && (
            <div className={`mb-4 p-4 rounded-lg ${
              message.type === 'success'
                ? 'bg-green-50 border border-green-200 text-green-700'
                : 'bg-red-50 border border-red-200 text-red-700'
            }`}>
              {message.text}
            </div>
          )}

          {loading ? (
            <div className="text-center py-8">
              <p className="text-gray-600">Loading accounts...</p>
            </div>
          ) : accounts.length === 0 ? (
            <div className="bg-primary/10 border border-primary/20 rounded-lg p-6 text-center">
              <p className="text-primary font-semibold mb-2">
                No accounts found
              </p>
              <p className="text-sm text-gray-600">
                Click the &quot;Populate Test Data&quot; button above to create sample accounts with positions
              </p>
            </div>
          ) : (
            <>
              {/* Portfolio Summary */}
              <div className="bg-gray-50 rounded-lg p-4 mb-6">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <p className="text-sm text-gray-600">Total Portfolio Value</p>
                    <p className="text-2xl font-bold text-primary">
                      ${calculatePortfolioTotal().toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Number of Accounts</p>
                    <p className="text-2xl font-bold text-dark">{accounts.length}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Total Positions</p>
                    <p className="text-2xl font-bold text-dark">
                      {accounts.reduce((sum, acc) => sum + (acc.positions?.length || 0), 0)}
                    </p>
                  </div>
                </div>
              </div>

              {/* Accounts List */}
              <div className="space-y-6">
                {accounts.map((account) => (
                  <div key={account.id} className="border border-gray-200 rounded-lg p-6">
                    <div className="mb-4">
                      <h3 className="text-xl font-semibold text-dark">{account.account_name}</h3>
                      <p className="text-sm text-gray-600">{account.account_purpose}</p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                      <div>
                        <p className="text-sm text-gray-600">Cash Balance</p>
                        <p className="font-semibold">
                          ${Number(account.cash_balance).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </p>
                      </div>
                      <div>
                        <p className="text-sm text-gray-600">Positions Value</p>
                        <p className="font-semibold">
                          ${(calculateAccountTotal(account) - Number(account.cash_balance)).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </p>
                      </div>
                      <div>
                        <p className="text-sm text-gray-600">Total Value</p>
                        <p className="font-semibold text-primary">
                          ${calculateAccountTotal(account).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </p>
                      </div>
                    </div>

                    {account.positions && account.positions.length > 0 && (
                      <div>
                        <h4 className="text-sm font-semibold text-gray-700 mb-2">Positions</h4>
                        <div className="bg-gray-50 rounded p-3">
                          <div className="grid grid-cols-3 md:grid-cols-4 gap-2 text-xs font-semibold text-gray-600 mb-2">
                            <div>Symbol</div>
                            <div className="text-right">Quantity</div>
                            <div className="text-right">Price</div>
                            <div className="text-right hidden md:block">Value</div>
                          </div>
                          {account.positions.map((position) => (
                            <div key={position.id} className="grid grid-cols-3 md:grid-cols-4 gap-2 text-sm py-1 border-t border-gray-200">
                              <div className="font-medium">{position.symbol}</div>
                              <div className="text-right">{Number(position.quantity).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}</div>
                              <div className="text-right">
                                ${position.current_price?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) || 'N/A'}
                              </div>
                              <div className="text-right hidden md:block">
                                ${((position.current_price || 0) * Number(position.quantity)).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </Layout>
  );
}