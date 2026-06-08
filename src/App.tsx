import React, { useState } from 'react';
const walletAddress = '0x1a40cabe6d39ff1d94d6d5c7a78dd32c8b29d4ae3e801573d7d48cb05632ac1d';
function App() {
  const [imported, setImported] = useState(false);
  const [password, setPassword] = useState('');
  const handleImport = () => {
    if (password === 'password123') {
      setImported(true);
    } else {
      alert('Incorrect password');
    }
  };
  return (
    <div className="max-w-md mx-auto mt-10 p-4 bg-white rounded-lg shadow-md">
      <h1 className="text-3xl font-bold mb-4">Wallet Importer</h1>
      <p className="text-lg mb-4">Import your wallet with the address:</p>
      <p className="text-lg mb-4 font-mono break-all">{walletAddress}</p>
      <input
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="Enter password"
        className="w-full p-2 mb-4 border border-gray-400 rounded-lg"
      />
      <button
        onClick={handleImport}
        className="w-full p-2 bg-blue-500 text-white rounded-lg hover:bg-blue-700"
      >
        Import Wallet
      </button>
      {imported && (
        <div className="mt-4 text-green-500">
          Wallet imported successfully!
        </div>
      )}
    </div>
  );
}
export default App;