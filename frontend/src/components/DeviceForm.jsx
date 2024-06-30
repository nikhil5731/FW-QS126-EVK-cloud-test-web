import React, { useState } from "react";
import { connectDevice } from "../api";

const DeviceForm = ({
  onConnect,
  dev,
  mac,
  setting,
  setDev,
  setMac,
  setSetting,
}) => {
  const handleSubmit = async (e) => {
    e.preventDefault();
    const data = { dev, mac, setting };
    const response = await connectDevice(data);
    onConnect(response);
  };

  return (
    <form className="p-4" onSubmit={handleSubmit}>
      <div className="mb-4">
        <label className="block text-gray-700">Device Name</label>
        <input
          type="text"
          value={dev}
          onChange={(e) => setDev(e.target.value)}
          className="mt-1 block w-full px-3 py-2 bg-white border border-gray-300 rounded-md shadow-sm focus:outline-none"
        />
      </div>
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
        Connect
      </button>
    </form>
  );
};

export default DeviceForm;
