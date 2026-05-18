"use client"

import React, { useState, useEffect } from 'react';
import { Plus, MapPin, CheckCircle, AlertTriangle, Loader2, Factory, Trash2, Edit, X, BookOpen } from 'lucide-react';
import { useDispatch, useSelector } from 'react-redux';
import { RootState, AppDispatch } from '../../store/store';
import { fetchMachines, registerMachine, deleteMachine, Machine } from '../../store/slices/machineSlice';

export default function MachineRegistryPage() {
  const dispatch = useDispatch<AppDispatch>();
  const { machines, loading } = useSelector((state: RootState) => state.machines);

  const [formData, setFormData] = useState<Machine>({
    machine_id: '',
    name: '',
    location: '',
    manual_id: ''
  });

  const [registerStatus, setRegisterStatus] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);

  useEffect(() => {
    dispatch(fetchMachines());
  }, [dispatch]);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setRegisterStatus(isEditing ? 'Updating...' : 'Registering...');
    try {
      await dispatch(registerMachine(formData)).unwrap();
      setRegisterStatus(isEditing ? 'Success! Machine updated.' : 'Success! Asset successfully registered in Context-Aware RAG.');
      setFormData({ machine_id: '', name: '', location: '', manual_id: '' });
      setIsEditing(false);
      setTimeout(() => setRegisterStatus(null), 3000);
    } catch (err) {
      setRegisterStatus(`Error: ${err}`);
      setTimeout(() => setRegisterStatus(null), 5000);
    }
  };

  const startEdit = (machine: Machine) => {
    setFormData(machine);
    setIsEditing(true);
    setRegisterStatus(null);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const cancelEdit = () => {
    setFormData({ machine_id: '', name: '', location: '', manual_id: '' });
    setIsEditing(false);
  };

  const handleDelete = async (id: string) => {
    if (!confirm(`Are you sure you want to decommission asset ${id}? This cannot be undone.`)) return;
    setDeletingId(id);
    try {
      await dispatch(deleteMachine(id)).unwrap();
    } catch (err) {
      alert(`Failed to delete: ${err}`);
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="p-4 md:p-8 max-w-6xl mx-auto text-slate-200">
      <header className="mb-8 md:mb-12">
        <h1 className="text-2xl md:text-4xl font-black text-white mb-2 flex items-center gap-3">
          <Factory className="text-blue-500" size={32} />
          Asset Registry
        </h1>
        <p className="text-slate-400 text-sm md:text-lg font-medium leading-relaxed">Enroll and manage physical machinery. Link assets directly to ingested PDF technical manuals.</p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Registration Form */}
        <div className="bg-slate-900/60 border border-slate-800 backdrop-blur-md rounded-2xl md:rounded-3xl p-6 md:p-8 shadow-2xl h-fit lg:sticky lg:top-24">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              {isEditing ? <Edit size={20} className="text-amber-400" /> : <Plus size={20} className="text-blue-400" />}
              {isEditing ? 'Update Machine' : 'Register New Machine'}
            </h2>
            {isEditing && (
              <button 
                onClick={cancelEdit}
                className="text-slate-500 hover:text-white transition-colors"
                title="Cancel Edit"
              >
                <X size={20} />
              </button>
            )}
          </div>

          <form onSubmit={handleRegister} className="space-y-5">
            <div>
              <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-2">Machine ID</label>
              <input 
                type="text" 
                required
                disabled={isEditing}
                value={formData.machine_id}
                onChange={(e) => setFormData({...formData, machine_id: e.target.value.toUpperCase().replace(/\s/g, '_')})}
                placeholder="e.g. PUMP-001" 
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-blue-500 transition-all text-white disabled:opacity-50 disabled:bg-slate-900 cursor-not-allowed"
              />
              {isEditing && <p className="text-[10px] text-amber-500/70 mt-1 font-medium italic">Asset ID cannot be modified after initial enrollment.</p>}
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-2">Asset Name</label>
              <input 
                type="text" 
                required
                value={formData.name}
                onChange={(e) => setFormData({...formData, name: e.target.value})}
                placeholder="e.g. Centrifugal Water Pump" 
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-blue-500 transition-all text-white"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-2">Physical Location</label>
              <input 
                type="text" 
                required
                value={formData.location}
                onChange={(e) => setFormData({...formData, location: e.target.value})}
                placeholder="e.g. Bay 4, Sector G" 
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-blue-500 transition-all text-white"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-2">Linked Manual ID</label>
              <input 
                type="text" 
                required
                value={formData.manual_id}
                onChange={(e) => setFormData({...formData, manual_id: e.target.value})}
                placeholder="e.g. centrifugal_pump_manual" 
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-blue-500 transition-all text-white"
              />
              <p className="text-[10px] text-slate-500 mt-1 font-medium italic">Must match the Manual ID registered in the technical PDF manual uploader page.</p>
            </div>

            <button 
              type="submit" 
              className={`w-full flex items-center justify-center gap-2 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-xl font-bold text-xs uppercase tracking-widest transition-all active:scale-[0.98] cursor-pointer`}
            >
              {isEditing ? 'Save Asset Modifications' : 'Enroll Physical Asset'}
            </button>
          </form>

          {registerStatus && (
            <div className={`mt-6 p-4 rounded-xl flex gap-3 text-xs ${
              registerStatus.includes('Error') 
                ? 'bg-red-500/10 border border-red-500/20 text-red-400' 
                : 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400'
            }`}>
              {registerStatus.includes('Error') ? <AlertTriangle size={16} /> : <CheckCircle size={16} />}
              <span>{registerStatus}</span>
            </div>
          )}
        </div>

        {/* Registered Machines List */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-slate-900/60 border border-slate-800 backdrop-blur-md rounded-2xl md:rounded-3xl p-6 md:p-8 shadow-2xl">
            <h2 className="text-xl font-bold text-white mb-6">Registered Assets ({machines.length})</h2>
            
            <div className="space-y-4">
              {machines.map((m) => (
                <div key={m.machine_id} className="flex flex-col md:flex-row md:items-center justify-between p-5 bg-slate-950 rounded-2xl border border-slate-800 hover:border-slate-700 transition-all gap-4">
                  <div className="space-y-2">
                    <div className="flex items-center gap-3">
                      <span className="text-xs font-black bg-blue-500/10 text-blue-400 border border-blue-500/20 px-2.5 py-0.5 rounded-lg">
                        {m.machine_id}
                      </span>
                      <h3 className="text-sm font-bold text-white">{m.name}</h3>
                    </div>

                    <div className="flex flex-wrap gap-x-6 gap-y-2 text-xs text-slate-500 font-medium">
                      <span className="flex items-center gap-1.5"><MapPin size={14} className="text-slate-600" /> {m.location}</span>
                      <span className="flex items-center gap-1.5"><BookOpen size={14} className="text-slate-600" /> Manual: {m.manual_id}</span>
                    </div>
                  </div>

                  <div className="flex gap-2">
                    <button 
                      onClick={() => startEdit(m)}
                      className="p-2.5 bg-slate-900 border border-slate-800 hover:border-amber-500/50 rounded-xl text-slate-400 hover:text-amber-400 transition-all cursor-pointer"
                      title="Edit Asset"
                    >
                      <Edit size={16} />
                    </button>
                    <button 
                      onClick={() => handleDelete(m.machine_id)}
                      disabled={deletingId === m.machine_id}
                      className="p-2.5 bg-slate-900 border border-slate-800 hover:border-red-500/50 rounded-xl text-slate-400 hover:text-red-500 transition-all disabled:opacity-50 cursor-pointer"
                      title="Decommission Asset"
                    >
                      {deletingId === m.machine_id ? <Loader2 size={16} className="animate-spin" /> : <Trash2 size={16} />}
                    </button>
                  </div>
                </div>
              ))}

              {machines.length === 0 && (
                <div className="text-center py-16 text-slate-600">
                  <AlertTriangle className="mx-auto mb-4 opacity-20" size={48} />
                  <p className="text-sm font-black uppercase tracking-wider">No assets registered yet</p>
                  <p className="text-xs font-medium text-slate-700 mt-1">Enroll your first machine using the panel on the left.</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
