// Post-script Ghidra (headless) : cartographie du chemin de rendu.
//
// Arguments : <fichier de sortie> <commande> [params...]
//   decomp  ADDR...            decompile chaque fonction (C) vers la sortie
//   callees ADDR DEPTH         arbre des appels sortants (profondeur DEPTH)
//   callers ADDR               fonctions appelantes
//   strings REGEX              chaines (adresse, texte) + fonctions qui les referencent
//   funcs                      toutes les fonctions (adresse, taille, nom)
//   consts HEX...              instructions dont un operande scalaire vaut HEX + fonction
import java.io.FileWriter;
import java.io.PrintWriter;
import java.util.*;
import java.util.regex.Pattern;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.data.StringDataInstance;
import ghidra.program.model.listing.*;
import ghidra.program.model.scalar.Scalar;
import ghidra.program.model.symbol.*;

public class Dump extends GhidraScript {
    PrintWriter out;

    @Override
    public void run() throws Exception {
        String[] a = getScriptArgs();
        out = new PrintWriter(new FileWriter(a[0], true));
        try {
            switch (a[1]) {
                case "decomp": for (int i = 2; i < a.length; i++) decomp(Long.decode(a[i])); break;
                case "callees": callees(Long.decode(a[2]), Integer.parseInt(a[3])); break;
                case "callers": callers(Long.decode(a[2])); break;
                case "strings": strings(a[2]); break;
                case "funcs": funcs(); break;
                case "consts": for (int i = 2; i < a.length; i++) consts(Long.decode(a[i])); break;
                default: println("commande inconnue " + a[1]);
            }
        } finally {
            out.close();
        }
    }

    Function fn(long addr) {
        Address ad = toAddr(addr);
        Function f = getFunctionContaining(ad);
        if (f == null) {
            f = createFunction(ad, null);
        }
        return f;
    }

    void decomp(long addr) throws Exception {
        Function f = fn(addr);
        DecompInterface ifc = new DecompInterface();
        ifc.openProgram(currentProgram);
        DecompileResults r = ifc.decompileFunction(f, 120, monitor);
        out.println("// ===== " + f.getName() + " @ " + f.getEntryPoint() + " (" + f.getBody().getNumAddresses() + " octets)");
        if (r.decompileCompleted()) {
            out.println(r.getDecompiledFunction().getC());
        } else {
            out.println("// echec : " + r.getErrorMessage());
        }
        ifc.dispose();
    }

    void callees(long addr, int depth) {
        Function f = fn(addr);
        Set<Function> seen = new HashSet<>();
        walk(f, 0, depth, seen);
    }

    void walk(Function f, int d, int max, Set<Function> seen) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < d; i++) sb.append("  ");
        sb.append(f.getEntryPoint()).append("  ").append(f.getName()).append("  (").append(f.getBody().getNumAddresses()).append(" o)");
        if (seen.contains(f)) { out.println(sb + "  [deja vu]"); return; }
        out.println(sb);
        seen.add(f);
        if (d >= max) return;
        // Appels dans l'ordre du code (references de type CALL), y compris les sauts terminaux.
        List<Function> kids = new ArrayList<>();
        InstructionIterator it = currentProgram.getListing().getInstructions(f.getBody(), true);
        while (it.hasNext()) {
            Instruction ins = it.next();
            for (Reference ref : ins.getReferencesFrom()) {
                if (ref.getReferenceType().isCall() || (ref.getReferenceType().isJump() && getFunctionContaining(ref.getToAddress()) != f)) {
                    Function k = getFunctionAt(ref.getToAddress());
                    if (k != null && !kids.contains(k)) kids.add(k);
                }
            }
        }
        for (Function k : kids) walk(k, d + 1, max, seen);
    }

    void callers(long addr) {
        Function f = fn(addr);
        out.println("// appelants de " + f.getName() + " @ " + f.getEntryPoint());
        ReferenceIterator it = currentProgram.getReferenceManager().getReferencesTo(f.getEntryPoint());
        while (it.hasNext()) {
            Reference r = it.next();
            Function c = getFunctionContaining(r.getFromAddress());
            out.println("  " + r.getFromAddress() + "  " + r.getReferenceType() + "  dans " + (c == null ? "?" : c.getName() + " @ " + c.getEntryPoint()));
        }
    }

    void strings(String regex) {
        Pattern p = Pattern.compile(regex.replace(',', '|'));
        DataIterator it = currentProgram.getListing().getDefinedData(true);
        while (it.hasNext()) {
            Data d = it.next();
            if (!d.hasStringValue()) continue;
            String s = StringDataInstance.getStringDataInstance(d).getStringValue();
            if (s == null || !p.matcher(s).find()) continue;
            out.println(d.getAddress() + "  " + s.replace("\n", "\\n"));
            ReferenceIterator rit = currentProgram.getReferenceManager().getReferencesTo(d.getAddress());
            while (rit.hasNext()) {
                Reference r = rit.next();
                Function f = getFunctionContaining(r.getFromAddress());
                out.println("    <- " + r.getFromAddress() + (f == null ? "" : "  " + f.getName() + " @ " + f.getEntryPoint()));
            }
        }
    }

    void funcs() {
        FunctionIterator it = currentProgram.getListing().getFunctions(true);
        while (it.hasNext()) {
            Function f = it.next();
            out.println(f.getEntryPoint() + "  " + f.getBody().getNumAddresses() + "  " + f.getName());
        }
    }

    void consts(long v) {
        out.println("// constante " + Long.toHexString(v));
        InstructionIterator it = currentProgram.getListing().getInstructions(true);
        while (it.hasNext()) {
            Instruction ins = it.next();
            for (int i = 0; i < ins.getNumOperands(); i++) {
                for (Object o : ins.getOpObjects(i)) {
                    if (o instanceof Scalar && ((Scalar) o).getUnsignedValue() == v) {
                        Function f = getFunctionContaining(ins.getAddress());
                        out.println("  " + ins.getAddress() + "  " + ins + (f == null ? "" : "   dans " + f.getName() + " @ " + f.getEntryPoint()));
                    }
                }
            }
        }
    }
}
