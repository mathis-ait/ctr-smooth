// Pré-script : dispose code.bin d'une ROM 3DS (base 0x00100000) et ajoute le .bss
// d'après l'ExHeader (tailles passées en arguments : bssStart bssSize).
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.mem.MemoryBlock;

public class CtrLayout extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] a = getScriptArgs();
        long bssStart = Long.decode(a[0]);
        long bssSize = Long.decode(a[1]);
        Memory mem = currentProgram.getMemory();
        MemoryBlock main = mem.getBlock(toAddr(0x00100000L));
        if (main != null) {
            main.setName("code");
            main.setExecute(true);
            main.setWrite(true);
        }
        if (mem.getBlock(".bss") == null) {
            MemoryBlock bss = mem.createUninitializedBlock(".bss", toAddr(bssStart), bssSize, false);
            bss.setRead(true);
            bss.setWrite(true);
            bss.setExecute(false);
        }
        println("CtrLayout: bss @" + Long.toHexString(bssStart) + " size " + Long.toHexString(bssSize));
    }
}
