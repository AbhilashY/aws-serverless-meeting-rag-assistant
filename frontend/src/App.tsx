import React, { useEffect, useState } from 'react';
import {
  getCurrentUser,
  signIn,
  signOut
} from 'aws-amplify/auth';

import './config/awsConfig';
import RAGQueryInterface from './components/RAGQueryInterface';
import './App.css';

interface User {
  username: string;
}

const App: React.FC = () => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    checkUser();
  }, []);

  const checkUser = async () => {
    try {
      const currentUser = await getCurrentUser();

      setUser({
        username: currentUser.username
      });
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async (
    event: React.FormEvent
  ) => {
    event.preventDefault();

    try {
      setError(null);

      const result = await signIn({
        username: email,
        password
      });

      if (result.isSignedIn) {
        await checkUser();
      } else {
        setError(
          `Additional authentication step required: ${result.nextStep.signInStep}`
        );
      }
    } catch (err: any) {
      console.error('Login error:', err);

      setError(
        err?.message ||
        'Unable to sign in. Please check your credentials.'
      );
    }
  };

  const handleLogout = async () => {
    try {
      await signOut();

      setUser(null);
      setEmail('');
      setPassword('');
    } catch (err) {
      console.error('Logout error:', err);

      setError(
        'Failed to logout. Please try again.'
      );
    }
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner"></div>
        <p>Loading...</p>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="login-container">
        <div className="login-box">
          <h1>🎥 Meeting RAG Assistant</h1>

          <p>
            Query your meeting transcripts with AI
          </p>

          <form onSubmit={handleLogin}>
            <input
              type="text"
              placeholder="Username or email"
              value={email}
              onChange={(event) =>
                setEmail(event.target.value)
              }
              required
            />

            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(event) =>
                setPassword(event.target.value)
              }
              required
            />

            <button
              type="submit"
              className="login-button"
            >
              Sign In
            </button>
          </form>

          {error && (
            <p className="error-message">
              {error}
            </p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="app-container">
      <RAGQueryInterface />

      <div className="user-menu">
        <span className="user-info">
          👤 {user.username}
        </span>

        <button
          className="logout-button"
          onClick={handleLogout}
        >
          Logout
        </button>
      </div>
    </div>
  );
};

export default App;
