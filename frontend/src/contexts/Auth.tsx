import {createContext,useContext,useEffect,useState,type ReactNode} from 'react';
import {api,type User} from '../lib/api';

type AuthValue={user:User|null;loading:boolean;refresh:()=>Promise<void>;logout:()=>Promise<void>};
const AuthContext=createContext<AuthValue|null>(null);
export function AuthProvider({children}:{children:ReactNode}) {
 const [user,setUser]=useState<User|null>(null),[loading,setLoading]=useState(true);
 const refresh=async()=>{try{setUser(await api<User>('/auth/me'));}catch{setUser(null);}finally{setLoading(false);}};
 useEffect(()=>{void refresh();},[]);
 const logout=async()=>{await api('/auth/logout',{method:'POST'});setUser(null);};
 return <AuthContext.Provider value={{user,loading,refresh,logout}}>{children}</AuthContext.Provider>;
}
export function useAuth(){const v=useContext(AuthContext);if(!v)throw Error('AuthProvider ausente');return v;}
