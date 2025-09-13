import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useAuth } from '@clerk/nextjs';
import Layout from '../components/Layout';
import { API_URL } from '../lib/config';

interface Job {
  id: string;
  created_at: string;
  status: string;
  job_type: string;
  result?: {
    report?: string;
    charts?: Record<string, unknown>;
    retirement?: Record<string, unknown>;
    recommendations?: string[];
  };
  error?: string;
}

export default function Analysis() {
  const router = useRouter();
  const { getToken } = useAuth();
  const { job_id } = router.query;
  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (job_id) {
      fetchJob(job_id as string);
    } else if (router.isReady) {
      // Router is ready but no job_id provided
      setLoading(false);
    }
  }, [job_id, router.isReady]);

  const fetchJob = async (jobId: string) => {
    try {
      const token = await getToken();
      const response = await fetch(`${API_URL}/api/jobs/${jobId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const jobData = await response.json();
        setJob(jobData);
      } else {
        console.error('Failed to fetch job');
      }
    } catch (error) {
      console.error('Error fetching job:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-US', {
      month: 'long',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <Layout>
        <div className="min-h-screen bg-gray-50 py-8">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="bg-white rounded-lg shadow px-8 py-12 text-center">
              <div className="animate-pulse">
                <div className="h-8 bg-gray-200 rounded w-1/3 mx-auto mb-4"></div>
                <div className="h-4 bg-gray-200 rounded w-1/2 mx-auto"></div>
              </div>
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  if (!job) {
    return (
      <Layout>
        <div className="min-h-screen bg-gray-50 py-8">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="bg-white rounded-lg shadow px-8 py-12 text-center">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">Analysis Not Found</h2>
              <p className="text-gray-600 mb-6">The requested analysis could not be found.</p>
              <button
                onClick={() => router.push('/advisor-team')}
                className="px-6 py-3 bg-primary text-white rounded-lg hover:bg-blue-600 font-semibold"
              >
                Back to Advisor Team
              </button>
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  if (job.status === 'running' || job.status === 'pending') {
    return (
      <Layout>
        <div className="min-h-screen bg-gray-50 py-8">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="bg-white rounded-lg shadow px-8 py-12 text-center">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">Analysis In Progress</h2>
              <p className="text-gray-600 mb-6">Your analysis is still being processed. Please check back in a few moments.</p>
              <div className="flex justify-center space-x-2 mb-6">
                <div className="w-3 h-3 bg-ai-accent rounded-full animate-pulse"></div>
                <div className="w-3 h-3 bg-ai-accent rounded-full animate-pulse delay-75"></div>
                <div className="w-3 h-3 bg-ai-accent rounded-full animate-pulse delay-150"></div>
              </div>
              <button
                onClick={() => fetchJob(job.id)}
                className="px-6 py-3 bg-primary text-white rounded-lg hover:bg-blue-600 font-semibold"
              >
                Refresh
              </button>
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  if (job.status === 'failed') {
    return (
      <Layout>
        <div className="min-h-screen bg-gray-50 py-8">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="bg-white rounded-lg shadow px-8 py-12">
              <h2 className="text-2xl font-bold text-red-600 mb-4">Analysis Failed</h2>
              <p className="text-gray-600 mb-4">The analysis encountered an error and could not be completed.</p>
              {job.error && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
                  <p className="text-sm text-red-800">{job.error}</p>
                </div>
              )}
              <button
                onClick={() => router.push('/advisor-team')}
                className="px-6 py-3 bg-primary text-white rounded-lg hover:bg-blue-600 font-semibold"
              >
                Try Another Analysis
              </button>
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="bg-white rounded-lg shadow px-8 py-6 mb-8">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-3xl font-bold text-dark mb-2">Portfolio Analysis Results</h1>
                <p className="text-gray-600">
                  Completed on {formatDate(job.created_at)}
                </p>
              </div>
              <button
                onClick={() => router.push('/advisor-team')}
                className="px-6 py-3 bg-ai-accent text-white rounded-lg hover:bg-purple-700 font-semibold"
              >
                New Analysis
              </button>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow px-8 py-6">
            <p className="text-gray-600 text-center py-12">
              Analysis results will be displayed here in Step 6 with charts, reports, and recommendations.
            </p>
            {job.result && (
              <div className="mt-6 p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-500 mb-2">Debug: Raw Result Data</p>
                <pre className="text-xs overflow-auto">{JSON.stringify(job.result, null, 2)}</pre>
              </div>
            )}
          </div>
        </div>
      </div>
    </Layout>
  );
}