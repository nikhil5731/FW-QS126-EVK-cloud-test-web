import React, { useState } from "react";
import { handleMode } from "../api";

const ModeForm = ({
  mode,
  onExecute,
  dev,
  mac,
  setMac,
  setting,
  setSetting,
}) => {
  const handleSubmit = async (e) => {
    e.preventDefault();
    const data = { dev, mac, setting };
    const response = await handleMode(mode, data);
    onExecute(response);
  };

  return (
    <form className="p-4" onSubmit={handleSubmit}>
      <div className="mb-4">
        <label className="block text-gray-700">MAC Address</label>
        <input
          type="text"
          value={mac}
          onChange={(e) => setMac(e.target.value)}
          className="mt-1 block w-full px-3 py-2 bg-white border border-gray-300 rounded-md shadow-sm focus:outline-none"
        />
      </div>
      <div className="mb-4">
        <label className="block text-gray-700">IC Settings ID</label>
        <input
          type="text"
          value={setting}
          onChange={(e) => setSetting(e.target.value)}
          className="mt-1 block w-full px-3 py-2 bg-white border border-gray-300 rounded-md shadow-sm focus:outline-none"
        />
      </div>
      <button
        type="submit"
        className="bg-blue-500 text-white py-2 px-4 rounded w-full"
      >
        Execute
      </button>
    </form>
  );
};

export default ModeForm;
