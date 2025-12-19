import React, { useState } from 'react';
import { humanRespond } from '../api/client';

interface Field {
    name: string;
    type: string;
    label?: string;
}

interface HumanInputModalProps {
    requestId: string;
    prompt: string;
    fields: Field[];
    contextData: any;
    onClose: () => void;
}

export const HumanInputModal: React.FC<HumanInputModalProps> = ({
    requestId,
    prompt,
    fields,
    contextData,
    onClose,
}) => {
    const [formData, setFormData] = useState<Record<string, any>>({});
    const [isSubmitting, setIsSubmitting] = useState(false);

    const handleInputChange = (name: string, value: any) => {
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const handleSubmit = async (approved: boolean) => {
        setIsSubmitting(true);
        try {
            await humanRespond(requestId, { ...formData, approved });
            onClose();
        } catch (error) {
            console.error("Failed to respond to human input request:", error);
            alert("Error sending response. Check console.");
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="fixed inset-0 z-[300] flex items-center justify-center bg-black/60 backdrop-blur-md">
            <div className="bg-white p-8 rounded-3xl shadow-2xl w-[500px] max-h-[90vh] overflow-y-auto transform transition-all border border-blue-100">
                <div className="flex items-center gap-3 mb-6">
                    <div className="h-10 w-10 bg-blue-100 rounded-full flex items-center justify-center text-blue-600">
                        👤
                    </div>
                    <h2 className="text-2xl font-bold text-gray-900">{prompt}</h2>
                </div>

                {contextData && (
                    <div className="mb-6 p-4 bg-gray-50 rounded-2xl border border-gray-100">
                        <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">Current Context / Result</label>
                        <pre className="text-sm text-gray-700 whitespace-pre-wrap font-mono bg-white p-3 rounded-xl border border-gray-100 shadow-inner">
                            {typeof contextData === 'object' ? JSON.stringify(contextData, null, 2) : String(contextData)}
                        </pre>
                    </div>
                )}

                <div className="space-y-6">
                    {fields.map(field => (
                        <div key={field.name}>
                            <label className="block text-sm font-semibold text-gray-700 mb-2">
                                {field.label || field.name}
                            </label>
                            {field.type === 'text' || field.type === 'string' ? (
                                <textarea
                                    className="w-full border border-gray-200 p-4 rounded-xl focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 outline-none transition-all min-h-[100px]"
                                    placeholder={`Enter ${field.name}...`}
                                    value={formData[field.name] || ''}
                                    onChange={e => handleInputChange(field.name, e.target.value)}
                                />
                            ) : field.type === 'boolean' ? (
                                <div className="flex items-center gap-3 mt-1">
                                    <input
                                        type="checkbox"
                                        id={`field-${field.name}`}
                                        className="w-5 h-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                        checked={formData[field.name] || false}
                                        onChange={e => handleInputChange(field.name, e.target.checked)}
                                    />
                                    <label htmlFor={`field-${field.name}`} className="text-gray-600">
                                        Yes / Confirm
                                    </label>
                                </div>
                            ) : (
                                <input
                                    type="text"
                                    className="w-full border border-gray-200 p-4 rounded-xl focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 outline-none transition-all"
                                    value={formData[field.name] || ''}
                                    onChange={e => handleInputChange(field.name, e.target.value)}
                                />
                            )}
                        </div>
                    ))}
                </div>

                <div className="mt-10 flex gap-4">
                    <button
                        onClick={() => handleSubmit(false)}
                        disabled={isSubmitting}
                        className="flex-1 px-6 py-4 bg-gray-100 text-gray-600 rounded-2xl hover:bg-gray-200 active:scale-95 transition-all font-bold disabled:opacity-50"
                    >
                        Reject / Stop
                    </button>
                    <button
                        onClick={() => handleSubmit(true)}
                        disabled={isSubmitting}
                        className="flex-[2] px-6 py-4 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-2xl hover:shadow-xl hover:shadow-blue-500/20 active:scale-95 transition-all font-bold disabled:opacity-50 flex items-center justify-center gap-2"
                    >
                        {isSubmitting ? (
                            <span className="h-5 w-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
                        ) : (
                            <>Confirm & Resume 🚀</>
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
};
